//! The binary cursor and LZMA transport. This module has no Python dependency.

use std::io::{self, Write};
use zerocopy::{FromBytes, Immutable, KnownLayout, Unaligned};

use liblzma::stream::{Action, LzmaOptions, Mode, Status, Stream};
use liblzma::write::XzEncoder;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReadError {
    Truncated {
        size: usize,
        offset: usize,
        length: usize,
    },
    Index,
    StringMarker(u8),
}

pub struct Reader<'a> {
    data: &'a [u8],
    offset: usize,
}

impl<'a> Reader<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, offset: 0 }
    }

    fn read<const N: usize>(&mut self) -> Result<[u8; N], ReadError> {
        let bytes = self.data.get(self.offset..).and_then(|rest| rest.get(..N));
        let bytes = bytes.ok_or(ReadError::Truncated {
            size: N,
            offset: self.offset,
            length: self.data.len(),
        })?;
        let mut result = [0; N];
        result.copy_from_slice(bytes);
        self.offset += N;
        Ok(result)
    }

    pub fn view<T: FromBytes + Immutable + KnownLayout + Unaligned>(
        &mut self,
    ) -> Result<&'a T, ReadError> {
        let error = ReadError::Truncated {
            size: std::mem::size_of::<T>(),
            offset: self.offset,
            length: self.data.len(),
        };
        let remaining = self.data.get(self.offset..).ok_or(error)?;
        let (value, _) = T::ref_from_prefix(remaining).map_err(|_| error)?;
        self.offset += std::mem::size_of::<T>();
        Ok(value)
    }

    pub fn byte(&mut self) -> Result<u8, ReadError> {
        self.read().map(u8::from_le_bytes)
    }

    pub fn int(&mut self) -> Result<u32, ReadError> {
        self.read().map(u32::from_le_bytes)
    }

    pub fn long(&mut self) -> Result<i64, ReadError> {
        self.read().map(i64::from_le_bytes)
    }

    pub fn string(&mut self) -> Result<Option<&'a [u8]>, ReadError> {
        let marker = *self.data.get(self.offset).ok_or(ReadError::Index)?;
        match marker {
            0 => {
                self.offset += 1;
                Ok(None)
            }
            11 => {
                self.offset += 1;
                let mut length = 0usize;
                let mut shift = 0;
                loop {
                    let byte = *self.data.get(self.offset).ok_or(ReadError::Index)?;
                    self.offset += 1;
                    let part = usize::from(byte & 0x7f);
                    if part != 0 {
                        if shift >= usize::BITS || part > (usize::MAX >> shift) {
                            // Oversized Python slice endpoints consume the rest
                            // of the buffer. Saturation gives the same behavior.
                            length = usize::MAX;
                        } else {
                            length |= part << shift;
                        }
                    }
                    if byte & 0x80 == 0 {
                        break;
                    }
                    shift = shift.saturating_add(7);
                }
                Ok(Some(self.slice(length)))
            }
            other => Err(ReadError::StringMarker(other)),
        }
    }

    /// Match Python slice semantics: a declared length can exceed available data.
    pub fn slice(&mut self, length: usize) -> &'a [u8] {
        let start = self.offset.min(self.data.len());
        self.offset = self.offset.saturating_add(length);
        &self.data[start..self.offset.min(self.data.len())]
    }

    pub fn replay_id(&mut self) -> Result<i64, ReadError> {
        self.long().or_else(|_| self.int().map(i64::from))
    }
}

pub fn write_string(output: &mut Vec<u8>, text: &[u8]) {
    output.push(11);
    let mut length = text.len();
    // Preserve the legacy writer's non-minimal encoding at bit-6 boundaries.
    loop {
        let byte = (length & 0x7f) as u8;
        length >>= 7;
        if length == 0 && byte & 0x40 == 0 {
            output.push(byte);
            break;
        }
        output.push(byte | 0x80);
    }
    output.extend_from_slice(text);
}

pub fn ticks_to_microseconds(ticks: i64) -> i64 {
    let microseconds = ticks.div_euclid(10);
    let remainder = ticks.rem_euclid(10);
    microseconds + i64::from(remainder > 5 || (remainder == 5 && microseconds % 2 != 0))
}

pub fn decompress(mut data: &[u8]) -> io::Result<Vec<u8>> {
    // Most replay streams expand several-fold. Reserve a bounded initial
    // buffer to avoid repeated reallocations; the checked loop still grows
    // without truncating streams that exceed this estimate.
    let capacity = data.len().saturating_mul(6).clamp(64 * 1024, 1024 * 1024);
    let mut output = Vec::with_capacity(capacity);
    let mut completed_stream = false;
    loop {
        let mut stream = Stream::new_auto_decoder(u64::MAX, 0)?;
        let start = output.len();
        loop {
            output.reserve(64 * 1024);
            let before_in = stream.total_in();
            let before_out = stream.total_out();
            let status = match stream.process_vec(data, &mut output, Action::Run) {
                Ok(status) => status,
                Err(_) if completed_stream => {
                    // Python ignores invalid trailing data after a complete
                    // stream, but never returns partially decoded trailing data.
                    output.truncate(start);
                    return Ok(output);
                }
                Err(error) => return Err(error.into()),
            };
            data = &data[(stream.total_in() - before_in) as usize..];
            if status == Status::StreamEnd {
                completed_stream = true;
                if data.is_empty() {
                    return Ok(output);
                }
                break;
            }
            if stream.total_in() == before_in && stream.total_out() == before_out {
                return Err(io::Error::new(
                    io::ErrorKind::UnexpectedEof,
                    "Compressed data ended before the end-of-stream marker was reached",
                ));
            }
        }
    }
}

pub fn compress(data: &[u8], dict_size: u32, mode: u32) -> io::Result<Vec<u8>> {
    // Python's custom FILTER_LZMA1 options start from preset 6, then override
    // dict_size and mode. Keep the remaining lc/lp/pb/nice_len/mf/depth defaults.
    let mut options = LzmaOptions::new_preset(6)?;
    let mode = match mode {
        1 => Mode::Fast,
        2 => Mode::Normal,
        _ => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "Invalid compression mode",
            ));
        }
    };
    options.dict_size(dict_size).mode(mode);
    let stream = Stream::new_lzma_encoder(&options)?;
    let mut encoder = XzEncoder::new_stream(Vec::new(), stream);
    encoder.write_all(data)?;
    encoder.finish()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn string_lengths_cover_legacy_boundaries_and_unicode() {
        for size in [0, 1, 63, 64, 127, 128, 8191, 8192] {
            let original = "é".repeat(size);
            let mut bytes = Vec::new();
            write_string(&mut bytes, original.as_bytes());
            assert_eq!(Reader::new(&bytes).string(), Ok(Some(original.as_bytes())));
        }
        let mut bytes = Vec::new();
        write_string(&mut bytes, &[b'x'; 64]);
        assert_eq!(&bytes[..3], &[11, 0xc0, 0]);
    }

    #[test]
    fn failed_long_read_does_not_consume_legacy_id() {
        let bytes = 1_127_598_189u32.to_le_bytes();
        assert_eq!(Reader::new(&bytes).replay_id(), Ok(1_127_598_189));
        for length in 0..4 {
            assert!(Reader::new(&bytes[..length]).replay_id().is_err());
        }
    }

    #[test]
    fn timestamp_rounding_is_exact_and_symmetric() {
        for (ticks, micros) in [(4, 0), (5, 0), (6, 1), (15, 2), (25, 2)] {
            assert_eq!(ticks_to_microseconds(ticks), micros);
            assert_eq!(ticks_to_microseconds(-ticks), -micros);
        }
        assert_eq!(
            ticks_to_microseconds(3_155_378_975_999_999_990),
            315_537_897_599_999_999
        );
    }

    #[test]
    fn lzma_alone_round_trip_with_both_modes() {
        let input = b"0|256|-500|0,16|128.0|64.0|5,-12345|0|0|123,";
        for mode in [1, 2] {
            let compressed = compress(input, 1 << 21, mode).unwrap();
            assert_eq!(decompress(&compressed).unwrap(), input);
        }
    }

    #[test]
    fn malformed_input_returns_errors() {
        assert_eq!(Reader::new(&[]).string(), Err(ReadError::Index));
        assert_eq!(
            Reader::new(&[10]).string(),
            Err(ReadError::StringMarker(10))
        );
        assert!(Reader::new(&[11, 0x80]).string().is_err());
        assert!(decompress(b"not an lzma stream").is_err());
        assert!(compress(b"test", 1 << 21, 99).is_err());
    }
}
