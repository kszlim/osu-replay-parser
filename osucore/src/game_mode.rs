use std::{
    collections::hash_map::DefaultHasher,
    hash::{Hash, Hasher},
};

use pyo3::{exceptions::PyValueError, prelude::*, pyclass::CompareOp};

#[pymethods]
impl GameMode {
    #[new]
    fn new(int: i32) -> GameMode {
        GameMode::from(int as i8)
    }
    #[getter]
    fn value(&self) -> i8 {
        *self as i8
    }
    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self == other),
            CompareOp::Ne => Ok(self != other),
            _ => PyResult::Err(PyValueError::new_err("Invalid comparison")),
        }
    }
    fn __hash__(&self) -> u64 {
        let mut hasher = DefaultHasher::new();
        self.hash(&mut hasher);
        hasher.finish()
    }
    fn __int__(&self) -> i32 {
        self.value() as i32
    }
    fn __bool__(&self) -> bool {
        self.value() != 0
    }
}

impl From<i8> for GameMode {
    fn from(int: i8) -> GameMode {
        match int {
            x if x == GameMode::STD as i8 => GameMode::STD,
            x if x == GameMode::TAIKO as i8 => GameMode::TAIKO,
            x if x == GameMode::CTB as i8 => GameMode::CTB,
            x if x == GameMode::MANIA as i8 => GameMode::MANIA,
            _ => GameMode::UNKNOWN,
        }
    }
}

#[derive(Default, Clone, Debug, Copy, PartialEq, Eq, Hash)]
#[pyclass]
pub enum GameMode {
    #[default]
    STD = 0,
    TAIKO = 1,
    CTB = 2,
    MANIA = 3,
    UNKNOWN,
}
