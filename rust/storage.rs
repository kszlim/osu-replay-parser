//! Fully decoded replay storage. No Python objects or callbacks are used here.

use std::sync::Arc;
use zerocopy::byteorder::{LittleEndian, U16, U32};
use zerocopy::{FromBytes, Immutable, IntoBytes, KnownLayout, Unaligned};

use crate::{codec, events::Frame};

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
pub struct Header {
    pub mode: u8,
    pub game_version: u32,
    pub strings: [Option<String>; 3],
    pub hits: [u16; 6],
    pub score: u32,
    pub max_combo: u16,
    pub perfect: u8,
    pub mods: u32,
    pub ticks: i64,
    pub replay_id: i64,
}

#[derive(Clone)]
pub struct ReplayStorage<I = i64, F = f64> {
    pub header: Header,
    pub lifebar: Option<Vec<(I, F)>>,
    pub frames: Arc<Vec<Frame<I, F>>>,
    pub seed: Option<I>,
}

pub enum EncodeError {
    Compression(std::io::Error),
    TooLong,
}

impl Header {
    pub fn encode(
        &self,
        life: &str,
        events: &str,
        dict_size: u32,
        mode: u32,
    ) -> Result<Vec<u8>, EncodeError> {
        let mut output = vec![self.mode];
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
        codec::write_string(&mut output, life.as_bytes());
        output.extend_from_slice(&self.ticks.to_le_bytes());
        let compressed = codec::compress(events.as_bytes(), dict_size, mode)
            .map_err(EncodeError::Compression)?;
        let length = u32::try_from(compressed.len()).map_err(|_| EncodeError::TooLong)?;
        output.extend_from_slice(&length.to_le_bytes());
        output.extend_from_slice(&compressed);
        output.extend_from_slice(&self.replay_id.to_le_bytes());
        Ok(output)
    }
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
        let mut life = String::new();
        for (time, value) in self.lifebar.iter().flatten() {
            write!(life, "{time}|").expect("writing to String cannot fail");
            if value.fract() == 0.0 {
                write!(life, "{}", *value as i64).expect("writing to String cannot fail");
            } else {
                crate::formatting::float(&mut life, *value);
            }
            life.push(',');
        }
        let mut events = String::with_capacity(self.frames.len().saturating_mul(32));
        for frame in self.frames.iter() {
            crate::formatting::frame(&mut events, *frame, legacy_flags);
        }
        if let Some(seed) = self.seed.filter(|seed| *seed != 0) {
            write!(events, "-12345|0|0|{seed},").expect("writing to String cannot fail");
        }
        self.header.encode(&life, &events, dict_size, mode)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::codec::Reader;

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
