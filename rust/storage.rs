//! Fully decoded replay storage. No Python objects or callbacks are used here.

use std::sync::Arc;
use zerocopy::byteorder::{LittleEndian, U16, U32};
use zerocopy::{FromBytes, Immutable, IntoBytes, KnownLayout, Unaligned};

use crate::{
    codec::{self, Reader},
    events::{self, Frame, Mode},
};

#[derive(FromBytes, Immutable, IntoBytes, KnownLayout, Unaligned)]
#[repr(C)]
pub struct ScoreWire {
    pub hits: [U16<LittleEndian>; 6],
    pub score: U32<LittleEndian>,
    pub max_combo: U16<LittleEndian>,
    pub perfect: u8,
    pub mods: U32<LittleEndian>,
}

#[derive(Clone)]
pub struct ReplayStorage {
    pub mode: u8,
    pub game_version: u32,
    pub strings: [Option<String>; 3],
    pub hits: [u16; 6],
    pub score: u32,
    pub max_combo: u16,
    pub perfect: u8,
    pub mods: u32,
    pub lifebar: Option<Vec<(i64, f64)>>,
    pub ticks: i64,
    pub frames: Arc<Vec<Frame>>,
    pub replay_id: i64,
    pub seed: Option<i64>,
}

pub enum EncodeError {
    Compression(std::io::Error),
    TooLong,
}

impl ReplayStorage {
    pub fn can_encode(&self) -> bool {
        self.lifebar.as_ref().is_none_or(|points| {
            points.iter().all(|(_, life)| {
                life.is_finite()
                    && (life.fract() != 0.0
                        || (*life >= i64::MIN as f64 && *life < -(i64::MIN as f64)))
            })
        })
    }

    pub fn encode(
        &self,
        dict_size: u32,
        mode: u32,
        legacy_flags: bool,
    ) -> Result<Vec<u8>, EncodeError> {
        use std::fmt::Write;
        let mut output = Vec::new();
        output.push(self.mode);
        output.extend_from_slice(&self.game_version.to_le_bytes());
        for value in &self.strings {
            codec::write_string(&mut output, value.as_deref().unwrap_or("").as_bytes());
        }
        let wire = ScoreWire {
            hits: self.hits.map(U16::new),
            score: U32::new(self.score),
            max_combo: U16::new(self.max_combo),
            perfect: self.perfect,
            mods: U32::new(self.mods),
        };
        output.extend_from_slice(wire.as_bytes());
        let mut life_text = String::new();
        if let Some(points) = &self.lifebar {
            for (time, life) in points {
                write!(life_text, "{time}|").expect("writing to String cannot fail");
                if life.fract() == 0.0 {
                    write!(life_text, "{}", *life as i64).expect("writing to String cannot fail");
                } else {
                    crate::formatting::float(&mut life_text, *life);
                }
                life_text.push(',');
            }
        }
        codec::write_string(&mut output, life_text.as_bytes());
        output.extend_from_slice(&(codec::ticks_to_microseconds(self.ticks) * 10).to_le_bytes());
        let mut events = String::with_capacity(self.frames.len().saturating_mul(32));
        for frame in self.frames.iter() {
            crate::formatting::frame(&mut events, *frame, legacy_flags);
        }
        if let Some(seed) = self.seed.filter(|seed| *seed != 0) {
            write!(events, "-12345|0|0|{seed},").expect("writing to String cannot fail");
        }
        let compressed = codec::compress(events.as_bytes(), dict_size, mode)
            .map_err(EncodeError::Compression)?;
        let length = u32::try_from(compressed.len()).map_err(|_| EncodeError::TooLong)?;
        output.extend_from_slice(&length.to_le_bytes());
        output.extend_from_slice(&compressed);
        output.extend_from_slice(&self.replay_id.to_le_bytes());
        Ok(output)
    }
}

/// The compatibility decoder remains authoritative for uncommon or invalid
/// inputs, including its Python exception types and arbitrary-size integers.
pub fn parse(data: &[u8]) -> Option<ReplayStorage> {
    let mut reader = Reader::new(data);
    let mode = reader.byte().ok()?;
    let kind = match mode {
        0 => Mode::Osu,
        1 => Mode::Taiko,
        2 => Mode::Catch,
        3 => Mode::Mania,
        _ => return None,
    };
    let game_version = reader.int().ok()?;
    let mut read_string = || -> Option<Option<String>> {
        reader
            .string()
            .ok()?
            .map(|bytes| std::str::from_utf8(bytes).map(str::to_owned))
            .transpose()
            .ok()
    };
    let strings = [read_string()?, read_string()?, read_string()?];
    let wire = reader.view::<ScoreWire>().ok()?;
    let hits = wire.hits.map(|number| number.get());
    let score = wire.score.get();
    let max_combo = wire.max_combo.get();
    let perfect = wire.perfect;
    let mods = wire.mods.get();
    let lifebar = match reader.string().ok()? {
        None | Some([]) => None,
        Some(bytes) => {
            let text = std::str::from_utf8(bytes).ok()?;
            let end = text.char_indices().next_back()?.0;
            let mut states = Vec::new();
            for entry in text[..end].split(',') {
                let mut fields = entry.split('|');
                let time = fields.next()?.trim().parse::<i64>().ok()?;
                let life = fields.next()?.trim().parse::<f64>().ok()?;
                states.push((time, life));
            }
            Some(states)
        }
    };
    let ticks = reader.long().ok()?;
    if !(0..=315_537_897_599_999_999).contains(&codec::ticks_to_microseconds(ticks)) {
        return None;
    }
    let length = reader.int().ok()? as usize;
    let decoded = codec::decompress(reader.slice(length)).ok()?;
    if !decoded.is_ascii() {
        return None;
    }
    let (frames, seed) = events::parse(std::str::from_utf8(&decoded).ok()?, kind).ok()?;
    let replay_id = reader.replay_id().ok()?;
    Some(ReplayStorage {
        mode,
        game_version,
        strings,
        hits,
        score,
        max_combo,
        perfect,
        mods,
        lifebar,
        ticks,
        frames: Arc::new(frames),
        replay_id,
        seed,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wire_view_is_unaligned_and_little_endian() {
        let mut data = [0u8; 24];
        data[1..3].copy_from_slice(&65535u16.to_le_bytes());
        data[13..17].copy_from_slice(&u32::MAX.to_le_bytes());
        let mut reader = Reader::new(&data[1..]);
        let wire = reader.view::<ScoreWire>().unwrap();
        assert_eq!(std::mem::size_of::<ScoreWire>(), 23);
        assert_eq!(std::mem::align_of::<ScoreWire>(), 1);
        assert_eq!(wire.hits[0].get(), 65535);
        assert_eq!(wire.score.get(), u32::MAX);
        assert!(Reader::new(&data[2..]).view::<ScoreWire>().is_err());
    }
}
