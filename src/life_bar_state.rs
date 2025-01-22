use pyo3::prelude::*;

#[derive(Default, Clone, Debug, PartialEq)]
#[pyclass]
pub struct LifeBarState {
    #[pyo3(get, set)]
    pub time: u32,
    #[pyo3(get, set)]
    pub life: f32,
}

#[pymethods]
impl LifeBarState {
    #[new]
    fn new(time: u32, life: f32) -> LifeBarState {
        LifeBarState { time, life }
    }
}
