//! Python conversions and I/O at the codec boundary.
//! Binary and event grammar live only in parse.rs; exceptional numbers use
//! Python builtins through the same decoder's Numbers interface.

use std::collections::HashMap;
use std::ffi::CStr;

use pyo3::exceptions::{PyIndexError, PyOverflowError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyBytes, PyDict, PyFloat, PyInt, PyList, PyString, PyType};

use crate::codec::{self, ReadError, Reader};
use crate::parse::{NativeNumbers, Numbers};
use crate::{events, formatting, models, parse, replay, sequence::ReplayData, storage};
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

fn parse_error<N>(
    py: Python<'_>,
    error: parse::Error<N>,
    number: impl FnOnce(N) -> PyErr,
) -> PyErr {
    match error {
        parse::Error::Read(error) => read_error(py, error),
        parse::Error::Utf8(bytes) => {
            decode(py, &bytes, c"utf-8").expect_err("decoder rejected UTF-8")
        }
        parse::Error::Ascii(bytes) => {
            decode(py, &bytes, c"ascii").expect_err("decoder rejected ASCII")
        }
        parse::Error::Mode(value) => {
            PyValueError::new_err(format!("{value} is not a valid GameMode"))
        }
        parse::Error::Timestamp => PyOverflowError::new_err("date value out of range"),
        parse::Error::Index => PyIndexError::new_err("list index out of range"),
        parse::Error::Compression(error) => exception(py, "lzma", "LZMAError", error.to_string()),
        parse::Error::Number(error) => number(error),
    }
}

struct Api<'py> {
    py: Python<'py>,
    legacy_flags: bool,
    int: Object<'py>,
    float: Object<'py>,
    utils: Bound<'py, PyModule>,
}

impl<'py> Numbers for Api<'py> {
    type Int = Bound<'py, PyInt>;
    type Float = Bound<'py, PyFloat>;
    type Error = PyErr;
    fn integer(&self, text: &str) -> PyResult<Self::Int> {
        Ok(self.int.call1((text,))?.cast_into()?)
    }
    fn float(&self, text: &str) -> PyResult<Self::Float> {
        Ok(self.float.call1((text,))?.cast_into()?)
    }
    fn int_eq(&self, value: &Self::Int, expected: i64) -> bool {
        value.extract::<i64>().ok() == Some(expected)
    }
    fn float_eq(&self, value: &Self::Float, expected: f64) -> bool {
        value.value() == expected
    }
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

    fn mode(&self, value: &Object<'py>) -> PyResult<EventKind> {
        let modes = self.utils.getattr("GameMode")?;
        for (mode, name) in [
            (EventKind::Osu, "STD"),
            (EventKind::Taiko, "TAIKO"),
            (EventKind::Catch, "CTB"),
            (EventKind::Mania, "MANIA"),
        ] {
            if value.is(modes.getattr(name)?) {
                return Ok(mode);
            }
        }
        Err(PyTypeError::new_err("mode must be a GameMode member"))
    }

    fn materialize(
        &self,
        frames: impl IntoIterator<Item = events::Frame<Bound<'py, PyInt>, Bound<'py, PyFloat>>>,
    ) -> PyResult<Py<ReplayData>> {
        let list = PyList::empty(self.py);
        for frame in frames {
            use events::Frame;
            let object = match frame {
                Frame::Base { time } => self.utils.getattr("ReplayEvent")?.call1((time,))?,
                Frame::Osu { time, x, y, keys } => self
                    .utils
                    .getattr("ReplayEventOsu")?
                    .call1((time, x, y, self.utils.getattr("Key")?.call1((keys,))?))?,
                Frame::Taiko { time, x, keys } => self
                    .utils
                    .getattr("ReplayEventTaiko")?
                    .call1((time, x, self.utils.getattr("KeyTaiko")?.call1((keys,))?))?,
                Frame::Catch { time, x, dashing } => self
                    .utils
                    .getattr("ReplayEventCatch")?
                    .call1((time, x, dashing))?,
                Frame::Mania { time, keys } => self
                    .utils
                    .getattr("ReplayEventMania")?
                    .call1((time, self.utils.getattr("KeyMania")?.call1((keys,))?))?,
            };
            list.append(object)?;
        }
        Py::new(self.py, ReplayData::from_list(list.unbind()))
    }

    fn events(
        &self,
        text: &str,
        mode: &Object<'py>,
    ) -> PyResult<(Py<ReplayData>, Option<Py<PyInt>>)> {
        let mode = self.mode(mode)?;
        match self.py.detach(|| parse::events(text, mode, &NativeNumbers)) {
            Ok((frames, seed)) => Ok((
                Py::new(self.py, ReplayData::from_frames(Arc::new(frames)))?,
                seed.map(|seed| PyInt::new(self.py, seed).unbind()),
            )),
            Err(parse::Error::Number(_)) => {
                let (frames, seed) = parse::events(text, mode, self)
                    .map_err(|error| parse_error(self.py, error, |error| error))?;
                Ok((self.materialize(frames)?, seed.map(Bound::unbind)))
            }
            Err(error) => Err(parse_error(self.py, error, |_| {
                PyValueError::new_err("invalid number")
            })),
        }
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
#[pyo3(signature = (data) -> "datetime")]
pub fn unpack_timestamp<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Object<'py>> {
    let ticks = Reader::new(data).long().map_err(|e| read_error(py, e))?;
    timestamp(py, ticks)
}

#[pyfunction]
pub fn unpack(py: Python<'_>, data: &[u8]) -> PyResult<Py<replay::Replay>> {
    match py.detach(|| parse::replay(data, &NativeNumbers)) {
        Ok(storage) => Py::new(py, replay::Replay::from_storage(storage)),
        Err(parse::Error::Number(_)) => {
            let api = Api::new(py)?;
            let decoded =
                parse::replay(data, &api).map_err(|error| parse_error(py, error, |error| error))?;
            let values = PyDict::new(py);
            let life = decoded
                .lifebar
                .map(|points| -> PyResult<_> {
                    let class = api.utils.getattr("LifeBarState")?;
                    PyList::new(
                        py,
                        points
                            .into_iter()
                            .map(|(time, life)| class.call1((time, life)))
                            .collect::<PyResult<Vec<_>>>()?,
                    )
                })
                .transpose()?;
            values.set_item("life_bar_graph", life)?;
            values.set_item("rng_seed", decoded.seed)?;
            values.set_item(
                "replay_data",
                api.materialize(decoded.frames.iter().cloned())?,
            )?;
            let storage = storage::ReplayStorage {
                header: decoded.header,
                lifebar: None,
                frames: Arc::new(Vec::new()),
                seed: None,
            };
            Py::new(py, replay::Replay::with_values(storage, values.unbind()))
        }
        Err(error) => Err(parse_error(py, error, |_| {
            PyValueError::new_err("invalid number")
        })),
    }
}

#[pyfunction]
#[pyo3(signature = (data: "str | bytes", *, decoded=false, decompressed=false, mode: "GameMode"))]
pub fn parse_replay_data<'py>(
    py: Python<'py>,
    data: &Object<'py>,
    decoded: bool,
    decompressed: bool,
    mode: &Object<'py>,
) -> PyResult<Py<ReplayData>> {
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

fn encode_error(py: Python<'_>, error: storage::EncodeError) -> PyErr {
    match error {
        storage::EncodeError::Compression(error) => {
            exception(py, "lzma", "LZMAError", error.to_string())
        }
        storage::EncodeError::TooLong => exception(py, "struct", "error", "argument out of range"),
    }
}

#[pyfunction]
#[pyo3(signature = (replay: "Replay", *, dict_size: "int | None"=None, mode: "int | None"=None))]
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
                .map_err(|error| encode_error(py, error))?;
            return Ok(PyBytes::new(py, &bytes));
        }
    }
    let api = Api::new(py)?;
    let mode_value = numeric_field(py, &replay.getattr("mode")?.getattr("value")?, false, 8)? as u8;
    let game_version = numeric_field(py, &replay.getattr("game_version")?, false, 32)? as u32;
    let mut strings = [None, None, None];
    for (slot, name) in strings
        .iter_mut()
        .zip(["beatmap_hash", "username", "replay_hash"])
    {
        let value = replay.getattr(name)?;
        if value.is_truthy()? {
            *slot = Some(value.extract::<String>()?);
        }
    }
    let mut hits = [0; 6];
    for (slot, name) in hits.iter_mut().zip([
        "count_300",
        "count_100",
        "count_50",
        "count_geki",
        "count_katu",
        "count_miss",
    ]) {
        *slot = numeric_field(py, &replay.getattr(name)?, false, 16)? as u16;
    }
    let score = numeric_field(py, &replay.getattr("score")?, false, 32)? as u32;
    let max_combo = numeric_field(py, &replay.getattr("max_combo")?, false, 16)? as u16;
    let perfect = numeric_field(py, &replay.getattr("perfect")?, false, 8)? as u8;
    let mods = numeric_field(py, &replay.getattr("mods")?.getattr("value")?, false, 32)? as u32;
    let life = pack_lifebar(&api, replay)?;
    let ticks = pack_timestamp(py, replay)?;
    let events = pack_events(&api, replay)?;
    if !events.is_ascii() {
        PyString::new(py, &events).call_method1("encode", ("ascii",))?;
    }
    let dict_size = compression_option(py, dict_size, 1 << 21)?;
    let mode = compression_option(py, mode, 1)?;
    let replay_id = numeric_field(py, &replay.getattr("replay_id")?, true, 64)? as i64;
    let header = storage::Header {
        mode: mode_value,
        game_version,
        strings,
        hits,
        score,
        max_combo,
        perfect,
        mods,
        ticks,
        replay_id,
    };
    let bytes = py
        .detach(|| header.encode(&life, &events, dict_size, mode))
        .map_err(|error| encode_error(py, error))?;
    Ok(PyBytes::new(py, &bytes))
}
