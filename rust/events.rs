//! Native event decoding and storage, independent of Python object allocation.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    Osu,
    Taiko,
    Catch,
    Mania,
}

#[derive(Clone, Copy, Debug)]
pub enum Frame {
    Base {
        time: i64,
    },
    Osu {
        time: i64,
        x: f64,
        y: f64,
        keys: i64,
    },
    Taiko {
        time: i64,
        x: i64,
        keys: i64,
    },
    Catch {
        time: i64,
        x: f64,
        dashing: bool,
    },
    Mania {
        time: i64,
        keys: i64,
    },
}

impl Frame {
    pub fn time(self) -> i64 {
        match self {
            Self::Base { time }
            | Self::Osu { time, .. }
            | Self::Taiko { time, .. }
            | Self::Catch { time, .. }
            | Self::Mania { time, .. } => time,
        }
    }

    pub fn keys(self) -> Option<i64> {
        match self {
            Self::Osu { keys, .. } | Self::Taiko { keys, .. } | Self::Mania { keys, .. } => {
                Some(keys)
            }
            _ => None,
        }
    }

    pub fn fields(self) -> &'static [&'static str] {
        match self {
            Self::Base { .. } => &["time_delta"],
            Self::Osu { .. } => &["time_delta", "x", "y", "keys"],
            Self::Taiko { .. } => &["time_delta", "x", "keys"],
            Self::Catch { .. } => &["time_delta", "x", "dashing"],
            Self::Mania { .. } => &["time_delta", "keys"],
        }
    }
}

/// Unusual Python numeric spellings, arbitrary-size integers and malformed
/// frames use the compatibility decoder. Never silently discard these inputs.
#[derive(Debug)]
pub struct NeedsCompatibility;

pub fn parse(text: &str, mode: Mode) -> Result<(Vec<Frame>, Option<i64>), NeedsCompatibility> {
    let mut entries = text.trim_end_matches(',').split(',').enumerate().peekable();
    let mut frames = Vec::with_capacity(text.len() / 24);
    let mut seed = None;
    while let Some((index, entry)) = entries.next() {
        let mut fields = entry.split('|');
        let time = integer(fields.next().ok_or(NeedsCompatibility)?)?;
        let x = fields.next().ok_or(NeedsCompatibility)?;
        let y = fields.next().ok_or(NeedsCompatibility)?;
        let keys = integer(fields.next().ok_or(NeedsCompatibility)?)?;
        if time == -12345 && entries.peek().is_none() {
            seed = Some(keys);
            continue;
        }
        if index < 2 && float(x)? == 256.0 && float(y)? == -500.0 {
            continue;
        }
        frames.push(match mode {
            Mode::Osu => Frame::Osu {
                time,
                x: float(x)?,
                y: float(y)?,
                keys,
            },
            Mode::Taiko => Frame::Taiko {
                time,
                x: integer(x)?,
                keys,
            },
            Mode::Catch => Frame::Catch {
                time,
                x: float(x)?,
                dashing: keys == 1,
            },
            Mode::Mania => Frame::Mania {
                time,
                keys: integer(x)?,
            },
        });
    }
    Ok((frames, seed))
}

fn integer(text: &str) -> Result<i64, NeedsCompatibility> {
    text.trim().parse().map_err(|_| NeedsCompatibility)
}

fn float(text: &str) -> Result<f64, NeedsCompatibility> {
    let value: f64 = text.trim().parse().map_err(|_| NeedsCompatibility)?;
    // Python dataclass equality also observes object identity for NaNs.
    // Keep non-finite values in Python storage through the compatibility path.
    if value.is_finite() {
        Ok(value)
    } else {
        Err(NeedsCompatibility)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sentinels_and_zero_seed_are_preserved() {
        let (frames, seed) = parse(
            "0|256|-500|0,0|256|-500|0,16|320|64|5,-12345|0|0|0,",
            Mode::Osu,
        )
        .unwrap();
        assert_eq!(frames.len(), 1);
        assert_eq!(frames[0].time(), 16);
        assert_eq!(frames[0].keys(), Some(5));
        assert_eq!(seed, Some(0));
    }

    #[test]
    fn unusual_inputs_request_compatibility_instead_of_truncating() {
        for text in ["", "1|0", "999999999999999999999|0|0|0,", "1_0|0|0|0,"] {
            assert!(parse(text, Mode::Osu).is_err());
        }
    }
}
