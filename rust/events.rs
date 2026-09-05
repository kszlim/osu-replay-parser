//! Native event decoding and storage, independent of Python object allocation.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    Osu,
    Taiko,
    Catch,
    Mania,
}

#[derive(Clone, Copy, Debug)]
pub enum Frame<I = i64, F = f64> {
    Base { time: I },
    Osu { time: I, x: F, y: F, keys: I },
    Taiko { time: I, x: I, keys: I },
    Catch { time: I, x: F, dashing: bool },
    Mania { time: I, keys: I },
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
