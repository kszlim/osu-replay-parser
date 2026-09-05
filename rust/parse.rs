//! One decoder for both native scalars and exceptional Python numeric values.
//! Normal decoding is monomorphized to Rust integers/floats and uses no Python.

use crate::{
    codec::{self, ReadError, Reader},
    events::{Frame, Mode},
    storage::{Header, ReplayStorage, ScoreWire},
};
use std::sync::Arc;

#[derive(Debug)]
pub enum Error<N> {
    Read(ReadError),
    Utf8(Vec<u8>),
    Ascii(Vec<u8>),
    Mode(u8),
    Timestamp,
    Index,
    Compression(std::io::Error),
    Number(N),
}
impl<N> From<ReadError> for Error<N> {
    fn from(error: ReadError) -> Self {
        Self::Read(error)
    }
}
impl<N> From<std::io::Error> for Error<N> {
    fn from(error: std::io::Error) -> Self {
        Self::Compression(error)
    }
}

pub trait Numbers {
    type Int;
    type Float;
    type Error;
    fn integer(&self, text: &str) -> Result<Self::Int, Self::Error>;
    fn float(&self, text: &str) -> Result<Self::Float, Self::Error>;
    fn int_eq(&self, value: &Self::Int, expected: i64) -> bool;
    fn float_eq(&self, value: &Self::Float, expected: f64) -> bool;
}

pub struct NativeNumbers;
#[derive(Debug)]
pub struct NeedsPython;

impl Numbers for NativeNumbers {
    type Int = i64;
    type Float = f64;
    type Error = NeedsPython;
    fn integer(&self, text: &str) -> Result<i64, NeedsPython> {
        use atoi::FromRadix10SignedChecked;
        let bytes = text.trim().as_bytes();
        if bytes.len() > 64 {
            return Err(NeedsPython);
        }
        let sign = usize::from(matches!(bytes.first(), Some(b'+' | b'-')));
        let (value, consumed) = i64::from_radix_10_signed_checked(bytes);
        if consumed == bytes.len() && consumed > sign {
            value.ok_or(NeedsPython)
        } else {
            Err(NeedsPython)
        }
    }
    fn float(&self, text: &str) -> Result<f64, NeedsPython> {
        let value: f64 = fast_float2::parse(text.trim()).map_err(|_| NeedsPython)?;
        // Python storage retains the interpreter's NaN equality behavior.
        if value.is_finite() {
            Ok(value)
        } else {
            Err(NeedsPython)
        }
    }
    fn int_eq(&self, value: &i64, expected: i64) -> bool {
        *value == expected
    }
    fn float_eq(&self, value: &f64, expected: f64) -> bool {
        *value == expected
    }
}

type ParsedEvents<P> = (
    Vec<Frame<<P as Numbers>::Int, <P as Numbers>::Float>>,
    Option<<P as Numbers>::Int>,
);
type ParsedReplay<P> = ReplayStorage<<P as Numbers>::Int, <P as Numbers>::Float>;

pub fn events<P: Numbers>(
    text: &str,
    mode: Mode,
    numbers: &P,
) -> Result<ParsedEvents<P>, Error<P::Error>> {
    let mut entries = text.trim_end_matches(',').split(',').enumerate().peekable();
    let mut frames = Vec::with_capacity(text.len() / 24);
    let mut seed = None;
    while let Some((index, entry)) = entries.next() {
        let mut fields = entry.split('|');
        let time = numbers
            .integer(fields.next().unwrap_or_default())
            .map_err(Error::Number)?;
        let x = fields.next().ok_or(Error::Index)?;
        let y = fields.next().ok_or(Error::Index)?;
        let keys = numbers
            .integer(fields.next().ok_or(Error::Index)?)
            .map_err(Error::Number)?;
        if numbers.int_eq(&time, -12345) && entries.peek().is_none() {
            seed = Some(keys);
            continue;
        }
        if index < 2
            && numbers.float_eq(&numbers.float(x).map_err(Error::Number)?, 256.0)
            && numbers.float_eq(&numbers.float(y).map_err(Error::Number)?, -500.0)
        {
            continue;
        }
        frames.push(match mode {
            Mode::Osu => Frame::Osu {
                time,
                x: numbers.float(x).map_err(Error::Number)?,
                y: numbers.float(y).map_err(Error::Number)?,
                keys,
            },
            Mode::Taiko => Frame::Taiko {
                time,
                x: numbers.integer(x).map_err(Error::Number)?,
                keys,
            },
            Mode::Catch => Frame::Catch {
                time,
                x: numbers.float(x).map_err(Error::Number)?,
                dashing: numbers.int_eq(&keys, 1),
            },
            Mode::Mania => Frame::Mania {
                time,
                keys: numbers.integer(x).map_err(Error::Number)?,
            },
        });
    }
    Ok((frames, seed))
}

fn string<N>(reader: &mut Reader<'_>) -> Result<Option<String>, Error<N>> {
    reader
        .string()?
        .map(|bytes| {
            std::str::from_utf8(bytes)
                .map(str::to_owned)
                .map_err(|_| Error::Utf8(bytes.to_vec()))
        })
        .transpose()
}

pub fn replay<P: Numbers>(data: &[u8], numbers: &P) -> Result<ParsedReplay<P>, Error<P::Error>> {
    let mut reader = Reader::new(data);
    let mode = reader.byte()?;
    let kind = match mode {
        0 => Mode::Osu,
        1 => Mode::Taiko,
        2 => Mode::Catch,
        3 => Mode::Mania,
        other => return Err(Error::Mode(other)),
    };
    let game_version = reader.int()?;
    let strings = [
        string(&mut reader)?,
        string(&mut reader)?,
        string(&mut reader)?,
    ];
    let wire = reader.view::<ScoreWire>()?;
    let hits = wire.hits.map(|value| value.get());
    let score = wire.score.get();
    let max_combo = wire.max_combo.get();
    let perfect = wire.perfect;
    let mods = wire.mods.get();
    let lifebar = match string(&mut reader)? {
        None => None,
        Some(text) if text.is_empty() => None,
        Some(text) => {
            let end = text
                .char_indices()
                .next_back()
                .map_or(0, |(index, _)| index);
            let mut states = Vec::new();
            for entry in text[..end].split(',') {
                let mut fields = entry.split('|');
                let time = numbers
                    .integer(fields.next().unwrap_or_default())
                    .map_err(Error::Number)?;
                let life = numbers
                    .float(fields.next().ok_or(Error::Index)?)
                    .map_err(Error::Number)?;
                states.push((time, life));
            }
            Some(states)
        }
    };
    let ticks = reader.long()?;
    if !(0..=315_537_897_599_999_999).contains(&codec::ticks_to_microseconds(ticks)) {
        return Err(Error::Timestamp);
    }
    let ticks = codec::ticks_to_microseconds(ticks) * 10;
    let length = reader.int()? as usize;
    let decoded = codec::decompress(reader.slice(length))?;
    if !decoded.is_ascii() {
        return Err(Error::Ascii(decoded));
    }
    let (frames, seed) = events(
        std::str::from_utf8(&decoded).expect("ASCII is UTF-8"),
        kind,
        numbers,
    )?;
    let replay_id = reader.replay_id()?;
    Ok(ReplayStorage {
        header: Header {
            mode,
            game_version,
            strings,
            hits,
            score,
            max_combo,
            perfect,
            mods,
            ticks,
            replay_id,
        },
        lifebar,
        frames: Arc::new(frames),
        seed,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sentinels_and_zero_seed_are_preserved() {
        let (frames, seed) = events(
            "0|256|-500|0,0|256|-500|0,16|320|64|5,-12345|0|0|0,",
            Mode::Osu,
            &NativeNumbers,
        )
        .unwrap();
        assert_eq!(frames.len(), 1);
        assert_eq!(frames[0].time(), 16);
        assert_eq!(frames[0].keys(), Some(5));
        assert_eq!(seed, Some(0));
    }
    #[test]
    fn unusual_inputs_request_python_instead_of_truncating() {
        for text in ["", "1|0", "999999999999999999999|0|0|0,", "1_0|0|0|0,"] {
            assert!(events(text, Mode::Osu, &NativeNumbers).is_err());
        }
    }
}
