use crate::flags::{Key, KeyMania, KeyTaiko};
use atoi::atoi;
use fast_float::parse;

use pyo3::class::basic::CompareOp;
use pyo3::prelude::*;

pub type ByteSlices<'a> = Vec<&'a [u8]>;

pub trait ReplayEvent {
    const MAGIC_NUMBER: i64 = -12345;
    fn time_delta(&self) -> i64;
    fn is_magic_number(&self) -> bool {
        self.time_delta() == Self::MAGIC_NUMBER
    }
    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool>;
}
use pyo3::exceptions::PyValueError;
impl ReplayEvent for ReplayEventOsu {
    fn time_delta(&self) -> i64 {
        self.time_delta
    }
    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self == other),
            CompareOp::Ne => Ok(self != other),
            _ => PyResult::Err(PyValueError::new_err("Invalid comparison")),
        }
    }
}

impl ReplayEvent for ReplayEventTaiko {
    fn time_delta(&self) -> i64 {
        self.time_delta
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self == other),
            CompareOp::Ne => Ok(self != other),
            _ => PyResult::Err(PyValueError::new_err("Invalid comparison")),
        }
    }
}

impl ReplayEvent for ReplayEventCatch {
    fn time_delta(&self) -> i64 {
        self.time_delta
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self == other),
            CompareOp::Ne => Ok(self != other),
            _ => PyResult::Err(PyValueError::new_err("Invalid comparison")),
        }
    }
}

impl ReplayEvent for ReplayEventMania {
    fn time_delta(&self) -> i64 {
        self.time_delta
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self == other),
            CompareOp::Ne => Ok(self != other),
            _ => PyResult::Err(PyValueError::new_err("Invalid comparison")),
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
#[pyclass]
pub struct ReplayEventOsu {
    #[pyo3(get, set)]
    time_delta: i64,
    #[pyo3(get, set)]
    x: f64,
    #[pyo3(get, set)]
    y: f64,
    #[pyo3(get, set)]
    keys: Key,
}

#[pymethods]
impl ReplayEventOsu {
    #[new]
    fn new(time_delta: i64, x: f64, y: f64, keys: Key) -> ReplayEventOsu {
        ReplayEventOsu {
            time_delta,
            x,
            y,
            keys,
        }
    }
    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        ReplayEvent::__richcmp__(self, other, op)
    }

    fn __repr__(&self) -> String {
        format!("{:?}", self)
    }
}
#[pymethods]
impl ReplayEventTaiko {
    #[new]
    fn new(time_delta: i64, x: i64, keys: KeyTaiko) -> ReplayEventTaiko {
        ReplayEventTaiko {
            time_delta,
            x,
            keys,
        }
    }
    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        ReplayEvent::__richcmp__(self, other, op)
    }
    fn __repr__(&self) -> String {
        format!("{:?}", self)
    }
}
#[pymethods]
impl ReplayEventCatch {
    #[new]
    fn new(time_delta: i64, x: f64, dashing: bool) -> ReplayEventCatch {
        ReplayEventCatch {
            time_delta,
            x,
            dashing,
        }
    }
    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        ReplayEvent::__richcmp__(self, other, op)
    }
    fn __repr__(&self) -> String {
        format!("{:?}", self)
    }
}
#[pymethods]
impl ReplayEventMania {
    #[new]
    fn new(time_delta: i64, keys: KeyMania) -> ReplayEventMania {
        ReplayEventMania { time_delta, keys }
    }
    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        ReplayEvent::__richcmp__(self, other, op)
    }
    fn __repr__(&self) -> String {
        format!("{:?}", self)
    }
}

pub struct ParseReplayEventErr;

impl TryFrom<ByteSlices<'_>> for ReplayEventOsu {
    fn try_from(event: ByteSlices) -> Result<ReplayEventOsu, ParseReplayEventErr> {
        if !event.is_empty() {
            if &event[0] == b"" {
                return Result::Err(ParseReplayEventErr);
            }
            let time_delta = atoi(event[0]).unwrap();
            let x = parse(event[1]).unwrap();
            let y = parse(event[2]).unwrap();
            let keys = atoi(event[3]).unwrap();
            let keys = Key(keys);
            Result::Ok(ReplayEventOsu {
                time_delta,
                x,
                y,
                keys,
            })
        } else {
            Result::Err(ParseReplayEventErr)
        }
    }

    type Error = ParseReplayEventErr;
}
impl TryFrom<ByteSlices<'_>> for ReplayEventTaiko {
    fn try_from(event: ByteSlices) -> Result<ReplayEventTaiko, ParseReplayEventErr> {
        if !event.is_empty() {
            if &event[0] == b"" {
                return Result::Err(ParseReplayEventErr);
            }
            let time_delta = atoi(event[0]).unwrap();
            let x = atoi(event[1]).unwrap();
            let key = atoi(event[3]).unwrap();
            let keys = KeyTaiko(key);
            Result::Ok(ReplayEventTaiko {
                time_delta,
                x,
                keys,
            })
        } else {
            Result::Err(ParseReplayEventErr)
        }
    }

    type Error = ParseReplayEventErr;
}
impl TryFrom<ByteSlices<'_>> for ReplayEventCatch {
    fn try_from(event: ByteSlices) -> Result<ReplayEventCatch, ParseReplayEventErr> {
        if !event.is_empty() {
            if &event[0] == b"" {
                return Result::Err(ParseReplayEventErr);
            }
            let time_delta = atoi(event[0]).unwrap();
            let x = parse(event[1]).unwrap();
            let key: i32 = atoi(event[3]).unwrap();
            Result::Ok(ReplayEventCatch {
                time_delta,
                x,
                dashing: key == 1,
            })
        } else {
            Result::Err(ParseReplayEventErr)
        }
    }

    type Error = ParseReplayEventErr;
}
impl TryFrom<ByteSlices<'_>> for ReplayEventMania {
    fn try_from(event: ByteSlices<'_>) -> Result<ReplayEventMania, ParseReplayEventErr> {
        if !event.is_empty() {
            if &event[0] == b"" {
                return Result::Err(ParseReplayEventErr);
            }
            let time_delta = atoi(event[0]).unwrap();
            let x = atoi(event[1]).unwrap();
            let keys = KeyMania(x);
            Result::Ok(ReplayEventMania { time_delta, keys })
        } else {
            Result::Err(ParseReplayEventErr)
        }
    }

    type Error = ParseReplayEventErr;
}

#[derive(Clone, Debug, PartialEq, Hash)]
#[pyclass]
pub struct ReplayEventTaiko {
    #[pyo3(get, set)]
    time_delta: i64,
    #[pyo3(get, set)]
    x: i64,
    #[pyo3(get, set)]
    keys: KeyTaiko,
}

#[derive(Clone, Debug, PartialEq)]
#[pyclass]
pub struct ReplayEventCatch {
    #[pyo3(get, set)]
    time_delta: i64,
    #[pyo3(get, set)]
    x: f64,
    #[pyo3(get, set)]
    dashing: bool,
}

#[derive(Clone, Debug, PartialEq)]
#[pyclass]
pub struct ReplayEventMania {
    #[pyo3(get, set)]
    time_delta: i64,
    #[pyo3(get, set)]
    keys: KeyMania,
}
