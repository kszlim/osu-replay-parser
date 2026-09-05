//! Python protocol adaptation for the native codec.
//!
//! Public models stay ordinary Python dataclasses and enums. The boundary uses
//! Python conversions for uncommon numeric spellings and unbounded integers,
//! preserving their semantics without penalizing ordinary replay frames.

use std::collections::HashMap;
use std::ffi::CStr;

use pyo3::exceptions::{PyIndexError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyBytes, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple, PyType};

use crate::codec::{self, ReadError, Reader};
use crate::{events, formatting, models, replay, sequence::ReplayData, storage};
use std::sync::Arc;

type Object<'py> = Bound<'py, PyAny>;

use crate::events::Mode as EventKind;

fn exception(py: Python<'_>, module: &str, name: &str, message: impl Into<String>) -> PyErr {
    match py
        .import(module)
        .and_then(|m| m.getattr(name))
        .and_then(|ty| ty.cast_into::<PyType>().map_err(Into::into))
    {
        Ok(ty) => PyErr::from_type(ty, message.into()),
        Err(error) => error,
    }
}

fn read_error(py: Python<'_>, error: ReadError) -> PyErr {
    match error {
        ReadError::Index => PyIndexError::new_err("index out of range"),
        ReadError::StringMarker(marker) => PyValueError::new_err(format!(
            "Expected the first byte of a string to be 0x00 or 0x0b, but got {marker}"
        )),
        ReadError::Truncated {
            size,
            offset,
            length,
        } => exception(
            py,
            "struct",
            "error",
            format!(
                "unpack_from requires a buffer of at least {} bytes for unpacking {size} bytes at offset {offset} (actual buffer size is {length})",
                offset.saturating_add(size)
            ),
        ),
    }
}

fn decode<'py>(py: Python<'py>, data: &[u8], encoding: &CStr) -> PyResult<Bound<'py, PyString>> {
    PyString::from_encoded_object(&PyBytes::new(py, data), Some(encoding), Some(c"strict"))
}

fn string<'py>(py: Python<'py>, reader: &mut Reader<'_>) -> PyResult<Object<'py>> {
    match reader.string().map_err(|e| read_error(py, e))? {
        Some(bytes) => Ok(decode(py, bytes, c"utf-8")?.into_any()),
        None => Ok(py.None().into_bound(py)),
    }
}

struct Api<'py> {
    py: Python<'py>,
    legacy_flags: bool,
    int: Object<'py>,
    float: Object<'py>,
    utils: Bound<'py, PyModule>,
}

impl<'py> Api<'py> {
    fn new(py: Python<'py>) -> PyResult<Self> {
        let builtins = py.import("builtins")?;
        Ok(Self {
            py,
            legacy_flags: py.version_info().minor < 11,
            int: builtins.getattr("int")?,
            float: builtins.getattr("float")?,
            utils: py.import("osrparse.utils")?,
        })
    }

    fn integer(&self, text: &str) -> PyResult<Object<'py>> {
        if let Ok(value) = text.trim().parse::<i64>() {
            Ok(PyInt::new(self.py, value).into_any())
        } else {
            self.int.call1((text,))
        }
    }

    fn float(&self, text: &str) -> PyResult<Object<'py>> {
        if let Ok(value) = text.trim().parse::<f64>() {
            Ok(PyFloat::new(self.py, value).into_any())
        } else {
            self.float.call1((text,))
        }
    }

    fn lifebar(&self, value: &Object<'py>) -> PyResult<Object<'py>> {
        if !value.is_truthy()? {
            return Ok(self.py.None().into_bound(self.py));
        }
        let text = value.cast::<PyString>()?.to_str()?;
        let end = text
            .char_indices()
            .next_back()
            .map_or(0, |(index, _)| index);
        let state_type = self.utils.getattr("LifeBarState")?;
        let result = PyList::empty(self.py);
        for entry in text[..end].split(',') {
            let mut parts = entry.split('|');
            let time = self.integer(parts.next().unwrap_or_default())?;
            let life = self.float(
                parts
                    .next()
                    .ok_or_else(|| PyIndexError::new_err("list index out of range"))?,
            )?;
            result.append(state_type.call1((time, life))?)?;
        }
        Ok(result.into_any())
    }

    fn events(&self, text: &str, mode: &Object<'py>) -> PyResult<(Object<'py>, Object<'py>)> {
        let modes = self.utils.getattr("GameMode")?;
        let selected = [
            (events::Mode::Osu, "STD"),
            (events::Mode::Taiko, "TAIKO"),
            (events::Mode::Catch, "CTB"),
            (events::Mode::Mania, "MANIA"),
        ]
        .into_iter()
        .find(|(_, name)| modes.getattr(*name).is_ok_and(|member| mode.is(member)));
        if let Some((kind, _)) = selected {
            if let Ok((frames, seed)) = self.py.detach(|| events::parse(text, kind)) {
                let data = Py::new(self.py, ReplayData::from_frames(Arc::new(frames)))?;
                return Ok((
                    data.into_bound(self.py).into_any(),
                    seed.into_pyobject(self.py)?.into_any(),
                ));
            }
        }
        let (data, seed) = self.events_compat(text, mode)?;
        Ok((data.into_any(), seed))
    }

    fn events_compat(
        &self,
        text: &str,
        mode: &Object<'py>,
    ) -> PyResult<(Bound<'py, PyList>, Object<'py>)> {
        let modes = self.utils.getattr("GameMode")?;
        let kinds = [
            (EventKind::Osu, "STD", "ReplayEventOsu", "Key"),
            (EventKind::Taiko, "TAIKO", "ReplayEventTaiko", "KeyTaiko"),
            (EventKind::Catch, "CTB", "ReplayEventCatch", "Key"),
            (EventKind::Mania, "MANIA", "ReplayEventMania", "KeyMania"),
        ];
        let mut selected = None;
        for (kind, name, event, keys) in kinds {
            if mode.is(modes.getattr(name)?) {
                selected = Some((kind, self.utils.getattr(event)?, self.utils.getattr(keys)?));
                break;
            }
        }
        let events = PyList::empty(self.py);
        let mut seed = self.py.None().into_bound(self.py);
        let mut flags = HashMap::<i64, Object<'py>>::new();
        let mut entries = text.trim_end_matches(',').split(',').enumerate().peekable();
        while let Some((index, entry)) = entries.next() {
            let mut parts = entry.split('|');
            let time = self.integer(parts.next().unwrap_or_default())?;
            let x = parts
                .next()
                .ok_or_else(|| PyIndexError::new_err("list index out of range"))?;
            let y = parts
                .next()
                .ok_or_else(|| PyIndexError::new_err("list index out of range"))?;
            let keys_text = parts
                .next()
                .ok_or_else(|| PyIndexError::new_err("list index out of range"))?;
            let keys = self.integer(keys_text)?;
            if time.eq(-12345)? && entries.peek().is_none() {
                seed = keys;
                continue;
            }
            if index < 2 && self.float(x)?.eq(256)? && self.float(y)?.eq(-500)? {
                continue;
            }
            let event = match &selected {
                Some((kind, event_type, key_type)) => match kind {
                    EventKind::Osu => event_type.call1((
                        time,
                        self.float(x)?,
                        self.float(y)?,
                        flag(&mut flags, key_type, keys)?,
                    ))?,
                    EventKind::Taiko => event_type.call1((
                        time,
                        self.integer(x)?,
                        flag(&mut flags, key_type, keys)?,
                    ))?,
                    EventKind::Catch => event_type.call1((time, self.float(x)?, keys.eq(1)?))?,
                    EventKind::Mania => {
                        event_type.call1((time, flag(&mut flags, key_type, self.integer(x)?)?))?
                    }
                },
                None => PyList::new(self.py, entry.split('|'))?.into_any(),
            };
            events.append(event)?;
        }
        Ok((events, seed))
    }
}

fn flag<'py>(
    cache: &mut HashMap<i64, Object<'py>>,
    class: &Object<'py>,
    value: Object<'py>,
) -> PyResult<Object<'py>> {
    if let Ok(key) = value.extract::<i64>() {
        if let Some(cached) = cache.get(&key) {
            return Ok(cached.clone());
        }
        let flag = class.call1((value,))?;
        cache.insert(key, flag.clone());
        Ok(flag)
    } else {
        class.call1((value,))
    }
}

pub(crate) fn timestamp<'py>(py: Python<'py>, ticks: i64) -> PyResult<Object<'py>> {
    let datetime = py.import("datetime")?;
    let keywords = PyDict::new(py);
    keywords.set_item("microseconds", codec::ticks_to_microseconds(ticks))?;
    let delta = datetime.getattr("timedelta")?.call((), Some(&keywords))?;
    let value = datetime
        .getattr("datetime")?
        .getattr("min")?
        .call_method1("__add__", (delta,))?;
    keywords.clear();
    keywords.set_item("tzinfo", datetime.getattr("timezone")?.getattr("utc")?)?;
    value.call_method("replace", (), Some(&keywords))
}

#[pyfunction]
pub fn unpack_timestamp<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Object<'py>> {
    let ticks = Reader::new(data).long().map_err(|e| read_error(py, e))?;
    timestamp(py, ticks)
}

#[pyfunction]
pub fn unpack<'py>(
    py: Python<'py>,
    data: &[u8],
    replay_type: &Object<'py>,
) -> PyResult<Object<'py>> {
    if let Some(storage) = py.detach(|| storage::parse(data)) {
        return Ok(Py::new(py, replay::Replay::from_storage(storage))?
            .into_bound(py)
            .into_any());
    }
    let api = Api::new(py)?;
    let mut reader = Reader::new(data);
    let mode = reader.byte().map_err(|e| read_error(py, e))?;
    let mode = api.utils.getattr("GameMode")?.call1((mode,))?;
    let mut fields = Vec::with_capacity(21);
    fields.push(mode.clone());
    fields.push(PyInt::new(py, reader.int().map_err(|e| read_error(py, e))?).into_any());
    for _ in 0..3 {
        fields.push(string(py, &mut reader)?);
    }
    for _ in 0..6 {
        fields.push(PyInt::new(py, reader.short().map_err(|e| read_error(py, e))?).into_any());
    }
    fields.push(PyInt::new(py, reader.int().map_err(|e| read_error(py, e))?).into_any());
    fields.push(PyInt::new(py, reader.short().map_err(|e| read_error(py, e))?).into_any());
    fields.push(PyInt::new(py, reader.byte().map_err(|e| read_error(py, e))?).into_any());
    fields.push(
        api.utils
            .getattr("Mod")?
            .call1((reader.int().map_err(|e| read_error(py, e))?,))?,
    );
    fields.push(api.lifebar(&string(py, &mut reader)?)?);
    fields.push(timestamp(
        py,
        reader.long().map_err(|e| read_error(py, e))?,
    )?);
    let length = reader.int().map_err(|e| read_error(py, e))? as usize;
    let compressed = reader.slice(length);
    let decoded = py
        .detach(|| codec::decompress(compressed))
        .map_err(|e| exception(py, "lzma", "LZMAError", e.to_string()))?;
    let decoded = decode(py, &decoded, c"ascii")?;
    let (events, seed) = api.events(decoded.to_str()?, &mode)?;
    fields.push(events.into_any());
    fields.push(PyInt::new(py, reader.replay_id().map_err(|e| read_error(py, e))?).into_any());
    fields.push(seed);
    replay_type.call1(PyTuple::new(py, fields)?)
}

#[pyfunction]
pub fn parse_events<'py>(
    py: Python<'py>,
    text: &str,
    mode: &Object<'py>,
) -> PyResult<(Object<'py>, Object<'py>)> {
    Api::new(py)?.events(text, mode)
}

#[pyfunction]
#[pyo3(signature = (data, *, decoded=false, decompressed=false, mode))]
pub fn parse_replay_data<'py>(
    py: Python<'py>,
    data: &Object<'py>,
    decoded: bool,
    decompressed: bool,
    mode: &Object<'py>,
) -> PyResult<Object<'py>> {
    let mut data = data.clone();
    if !decoded && !decompressed {
        data = py.import("base64")?.getattr("b64decode")?.call1((data,))?;
    }
    if !decompressed {
        let bytes: Vec<u8> = data.extract()?;
        let bytes = py
            .detach(|| codec::decompress(&bytes))
            .map_err(|e| exception(py, "lzma", "LZMAError", e.to_string()))?;
        if bytes.is_ascii() {
            let text = std::str::from_utf8(&bytes).expect("ASCII is valid UTF-8");
            return Api::new(py)?.events(text, mode).map(|(events, _)| events);
        }
        data = decode(py, &bytes, c"ascii")?.into_any();
    }
    let text = data.cast::<PyString>()?.to_str()?;
    Api::new(py)?.events(text, mode).map(|(events, _)| events)
}

fn numeric_field(py: Python<'_>, value: &Object<'_>, signed: bool, bits: u8) -> PyResult<i128> {
    let index = py
        .import("operator")?
        .getattr("index")?
        .call1((value,))
        .map_err(|_| exception(py, "struct", "error", "required argument is not an integer"))?;
    let number = index
        .extract::<i128>()
        .map_err(|_| exception(py, "struct", "error", "argument out of range"))?;
    let (min, max) = if signed {
        (-(1i128 << (bits - 1)), (1i128 << (bits - 1)) - 1)
    } else {
        (0, (1i128 << bits) - 1)
    };
    if !(min..=max).contains(&number) {
        return Err(exception(py, "struct", "error", "argument out of range"));
    }
    Ok(number)
}

fn write_field(
    py: Python<'_>,
    output: &mut Vec<u8>,
    value: &Object<'_>,
    signed: bool,
    bits: u8,
) -> PyResult<()> {
    let number = numeric_field(py, value, signed, bits)?;
    output.extend_from_slice(&number.to_le_bytes()[..usize::from(bits / 8)]);
    Ok(())
}

fn write_python_string(output: &mut Vec<u8>, value: &Object<'_>) -> PyResult<()> {
    if value.is_truthy()? {
        let encoded = value.call_method1("encode", ("utf-8",))?;
        codec::write_string(output, encoded.cast::<PyBytes>()?.as_bytes());
    } else {
        codec::write_string(output, b"");
    }
    Ok(())
}

fn append_display(output: &mut String, value: &Object<'_>) -> PyResult<()> {
    // Python's shortest float representation differs from Rust's (notably
    // exponents, integral floats and negative zero). Preserve the wire text.
    output.push_str(value.str()?.to_str()?);
    Ok(())
}

fn pack_timestamp(py: Python<'_>, replay: &Object<'_>) -> PyResult<i64> {
    let datetime = py.import("datetime")?;
    let utc = datetime.getattr("timezone")?.getattr("utc")?;
    let value = replay
        .getattr("timestamp")?
        .call_method1("astimezone", (&utc,))?;
    let kwargs = PyDict::new(py);
    kwargs.set_item("tzinfo", utc)?;
    let epoch =
        datetime
            .getattr("datetime")?
            .getattr("min")?
            .call_method("replace", (), Some(&kwargs))?;
    let delta = value.call_method1("__sub__", (epoch,))?;
    let days: i64 = delta.getattr("days")?.extract()?;
    let seconds: i64 = delta.getattr("seconds")?.extract()?;
    let microseconds: i64 = delta.getattr("microseconds")?.extract()?;
    Ok(((days * 86_400 + seconds) * 1_000_000 + microseconds) * 10)
}

fn pack_lifebar(api: &Api<'_>, replay: &Object<'_>) -> PyResult<String> {
    let states = replay.getattr("life_bar_graph")?;
    let mut output = String::new();
    if states.is_none() {
        return Ok(output);
    }
    for state in states.try_iter()? {
        let state = state?;
        append_display(&mut output, &state.getattr("time")?)?;
        output.push('|');
        let life = state.getattr("life")?;
        let integer = api.int.call1((&life,))?;
        append_display(
            &mut output,
            if integer.eq(&life)? { &integer } else { &life },
        )?;
        output.push(',');
    }
    Ok(output)
}

fn append_event(api: &Api<'_>, event: &Object<'_>, output: &mut String) -> PyResult<()> {
    if event.is_exact_instance_of::<models::ReplayEventOsu>()
        || event.is_exact_instance_of::<models::ReplayEventTaiko>()
        || event.is_exact_instance_of::<models::ReplayEventCatch>()
        || event.is_exact_instance_of::<models::ReplayEventMania>()
    {
        let native = event.cast::<models::ReplayEvent>()?.borrow();
        if native.is_native() {
            formatting::frame(output, native.frame, api.legacy_flags);
            return Ok(());
        }
    }
    let time = event.getattr("time_delta")?;
    let kind = if event.is_instance(&api.utils.getattr("ReplayEventOsu")?)? {
        EventKind::Osu
    } else if event.is_instance(&api.utils.getattr("ReplayEventTaiko")?)? {
        EventKind::Taiko
    } else if event.is_instance(&api.utils.getattr("ReplayEventCatch")?)? {
        EventKind::Catch
    } else if event.is_instance(&api.utils.getattr("ReplayEventMania")?)? {
        EventKind::Mania
    } else {
        return Ok(());
    };
    append_display(output, &time)?;
    output.push('|');
    if kind == EventKind::Mania {
        append_display(output, &event.getattr("keys")?.getattr("value")?)?;
        output.push_str("|0|0,");
    } else {
        append_display(output, &event.getattr("x")?)?;
        output.push('|');
        if kind == EventKind::Osu {
            append_display(output, &event.getattr("y")?)?;
            output.push('|');
        } else {
            output.push_str("0|");
        }
        if kind == EventKind::Catch {
            append_display(output, &api.int.call1((event.getattr("dashing")?,))?)?;
        } else {
            append_display(output, &event.getattr("keys")?.getattr("value")?)?;
        }
        output.push(',');
    }
    Ok(())
}

fn pack_events(api: &Api<'_>, replay: &Object<'_>) -> PyResult<String> {
    let events = replay.getattr("replay_data")?;
    let native = if let Ok(sequence) = events.cast::<ReplayData>() {
        let data = sequence.borrow();
        if data.materialized.is_none() {
            Some((
                data.frames.clone(),
                data.cache
                    .iter()
                    .map(|(i, event)| (*i, event.clone_ref(api.py)))
                    .collect::<HashMap<_, _>>(),
            ))
        } else {
            None
        }
    } else {
        None
    };
    let mut output = String::with_capacity(events.len().unwrap_or(0).saturating_mul(32));
    if let Some((frames, cache)) = native {
        for (index, frame) in frames.iter().enumerate() {
            if let Some(event) = cache.get(&index) {
                let unchanged = event
                    .bind(api.py)
                    .cast::<models::ReplayEvent>()?
                    .borrow()
                    .is_native();
                if !unchanged {
                    append_event(api, event.bind(api.py), &mut output)?;
                    continue;
                }
            }
            formatting::frame(&mut output, *frame, api.legacy_flags);
        }
    } else {
        for event in events.try_iter()? {
            append_event(api, &event?, &mut output)?;
        }
    }
    let seed = replay.getattr("rng_seed")?;
    if seed.is_truthy()? {
        output.push_str("-12345|0|0|");
        append_display(&mut output, &seed)?;
        output.push(',');
    }
    Ok(output)
}

#[pyfunction]
pub fn _format_float(value: f64) -> String {
    let mut output = String::new();
    formatting::float(&mut output, value);
    output
}

fn compression_option(py: Python<'_>, value: Option<&Object<'_>>, default: u32) -> PyResult<u32> {
    match value {
        None => Ok(default),
        Some(value) if !value.is_truthy()? => Ok(default),
        Some(value) => py
            .import("operator")?
            .getattr("index")?
            .call1((value,))
            .and_then(|value| value.extract::<u32>())
            .map_err(|_| PyValueError::new_err("Invalid filter specifier for LZMA filter")),
    }
}

#[pyfunction]
#[pyo3(signature = (replay, *, dict_size=None, mode=None))]
pub fn pack<'py>(
    py: Python<'py>,
    replay: &Object<'py>,
    dict_size: Option<&Object<'py>>,
    mode: Option<&Object<'py>>,
) -> PyResult<Bound<'py, PyBytes>> {
    if let Ok(native) = replay.cast::<replay::Replay>() {
        let snapshot = native.borrow().native_snapshot(py)?;
        if let Some(snapshot) = snapshot {
            let dict_size = compression_option(py, dict_size, 1 << 21)?;
            let mode = compression_option(py, mode, 1)?;
            let legacy_flags = py.version_info().minor < 11;
            let bytes = py
                .detach(|| snapshot.encode(dict_size, mode, legacy_flags))
                .map_err(|error| match error {
                    storage::EncodeError::Compression(error) => {
                        exception(py, "lzma", "LZMAError", error.to_string())
                    }
                    storage::EncodeError::TooLong => {
                        exception(py, "struct", "error", "argument out of range")
                    }
                })?;
            return Ok(PyBytes::new(py, &bytes));
        }
    }
    let api = Api::new(py)?;
    let mut output = Vec::new();
    write_field(
        py,
        &mut output,
        &replay.getattr("mode")?.getattr("value")?,
        false,
        8,
    )?;
    write_field(py, &mut output, &replay.getattr("game_version")?, false, 32)?;
    for name in ["beatmap_hash", "username", "replay_hash"] {
        write_python_string(&mut output, &replay.getattr(name)?)?;
    }
    for name in [
        "count_300",
        "count_100",
        "count_50",
        "count_geki",
        "count_katu",
        "count_miss",
    ] {
        write_field(py, &mut output, &replay.getattr(name)?, false, 16)?;
    }
    write_field(py, &mut output, &replay.getattr("score")?, false, 32)?;
    write_field(py, &mut output, &replay.getattr("max_combo")?, false, 16)?;
    write_field(py, &mut output, &replay.getattr("perfect")?, false, 8)?;
    write_field(
        py,
        &mut output,
        &replay.getattr("mods")?.getattr("value")?,
        false,
        32,
    )?;
    codec::write_string(&mut output, pack_lifebar(&api, replay)?.as_bytes());
    output.extend_from_slice(&pack_timestamp(py, replay)?.to_le_bytes());
    let events = pack_events(&api, replay)?;
    // Match the original ASCII encoder's exception for invalid user edits.
    if !events.is_ascii() {
        PyString::new(py, &events).call_method1("encode", ("ascii",))?;
    }
    let dict_size = compression_option(py, dict_size, 1 << 21)?;
    let mode = compression_option(py, mode, 1)?;
    let compressed = py
        .detach(|| codec::compress(events.as_bytes(), dict_size, mode))
        .map_err(|e| exception(py, "lzma", "LZMAError", e.to_string()))?;
    let length = u32::try_from(compressed.len())
        .map_err(|_| exception(py, "struct", "error", "argument out of range"))?;
    output.extend_from_slice(&length.to_le_bytes());
    output.extend_from_slice(&compressed);
    write_field(py, &mut output, &replay.getattr("replay_id")?, true, 64)?;
    Ok(PyBytes::new(py, &output))
}
