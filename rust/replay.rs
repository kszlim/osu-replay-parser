//! One Python object around an entirely Rust-owned decoded replay.

use crate::{bindings, sequence::ReplayData, storage::ReplayStorage};
use pyo3::exceptions::PyAttributeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};

const FIELDS: &[&str] = &[
    "mode",
    "game_version",
    "beatmap_hash",
    "username",
    "replay_hash",
    "count_300",
    "count_100",
    "count_50",
    "count_geki",
    "count_katu",
    "count_miss",
    "score",
    "max_combo",
    "perfect",
    "mods",
    "life_bar_graph",
    "timestamp",
    "replay_data",
    "replay_id",
    "rng_seed",
];

#[pyclass(subclass, weakref, module = "osrparse.replay")]
pub struct Replay {
    storage: Option<ReplayStorage>,
    values: Option<Py<PyDict>>,
    header_dirty: bool,
}

impl Replay {
    pub fn from_storage(storage: ReplayStorage) -> Self {
        Self {
            storage: Some(storage),
            values: None,
            header_dirty: false,
        }
    }

    pub fn native_snapshot(&self, py: Python<'_>) -> PyResult<Option<ReplayStorage>> {
        let Some(storage) = &self.storage else {
            return Ok(None);
        };
        if self.header_dirty || !storage.can_encode() {
            return Ok(None);
        }
        let mut snapshot = storage.clone();
        if let Some(values) = &self.values {
            if let Some(data) = values.bind(py).get_item("replay_data")? {
                let Ok(sequence) = data.cast::<ReplayData>() else {
                    return Ok(None);
                };
                let sequence = sequence.borrow();
                if sequence.materialized.is_some() {
                    return Ok(None);
                }
                for event in sequence.cache.values() {
                    if !event
                        .bind(py)
                        .cast::<crate::models::ReplayEvent>()?
                        .borrow()
                        .is_native()
                    {
                        return Ok(None);
                    }
                }
                snapshot.frames = sequence.frames.clone();
            }
        }
        Ok(Some(snapshot))
    }

    fn values<'py>(&mut self, py: Python<'py>) -> Bound<'py, PyDict> {
        self.values
            .get_or_insert_with(|| PyDict::new(py).unbind())
            .bind(py)
            .clone()
    }

    fn field<'py>(&mut self, py: Python<'py>, name: &str) -> PyResult<Bound<'py, PyAny>> {
        if let Some(values) = &self.values {
            if let Some(value) = values.bind(py).get_item(name)? {
                return Ok(value);
            }
        }
        let s = self
            .storage
            .as_ref()
            .ok_or_else(|| PyAttributeError::new_err(name.to_owned()))?;
        let value = match name {
            "mode" => py
                .import("osrparse.utils")?
                .getattr("GameMode")?
                .call1((s.mode,))?,
            "mods" => py
                .import("osrparse.utils")?
                .getattr("Mod")?
                .call1((s.mods,))?,
            "game_version" => s.game_version.into_pyobject(py)?.into_any(),
            "beatmap_hash" => s.strings[0].as_deref().into_pyobject(py)?.into_any(),
            "username" => s.strings[1].as_deref().into_pyobject(py)?.into_any(),
            "replay_hash" => s.strings[2].as_deref().into_pyobject(py)?.into_any(),
            "count_300" => s.hits[0].into_pyobject(py)?.into_any(),
            "count_100" => s.hits[1].into_pyobject(py)?.into_any(),
            "count_50" => s.hits[2].into_pyobject(py)?.into_any(),
            "count_geki" => s.hits[3].into_pyobject(py)?.into_any(),
            "count_katu" => s.hits[4].into_pyobject(py)?.into_any(),
            "count_miss" => s.hits[5].into_pyobject(py)?.into_any(),
            "score" => s.score.into_pyobject(py)?.into_any(),
            "max_combo" => s.max_combo.into_pyobject(py)?.into_any(),
            "perfect" => s.perfect.into_pyobject(py)?.into_any(),
            "timestamp" => bindings::timestamp(py, s.ticks)?,
            "replay_id" => s.replay_id.into_pyobject(py)?.into_any(),
            "rng_seed" => s.seed.into_pyobject(py)?.into_any(),
            "replay_data" => Py::new(py, ReplayData::from_frames(s.frames.clone()))?
                .into_bound(py)
                .into_any(),
            "life_bar_graph" => match &s.lifebar {
                None => py.None().into_bound(py),
                Some(points) => {
                    let class = py.import("osrparse.utils")?.getattr("LifeBarState")?;
                    let mut values = Vec::with_capacity(points.len());
                    for (time, life) in points {
                        values.push(class.call1((*time, *life))?);
                    }
                    PyList::new(py, values)?.into_any()
                }
            },
            _ => return Err(PyAttributeError::new_err(name.to_owned())),
        };
        self.values(py).set_item(name, &value)?;
        if name == "life_bar_graph" && !value.is_none() {
            self.header_dirty = true;
        }
        if name == "replay_data" {
            if let Some(storage) = &mut self.storage {
                storage.frames = std::sync::Arc::new(Vec::new());
            }
        }
        Ok(value)
    }

    fn materialize<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        if self.storage.is_some() {
            for name in FIELDS {
                self.field(py, name)?;
            }
        }
        let values = self.values(py);
        if let Some(data) = values.get_item("replay_data")? {
            if let Ok(sequence) = data.cast::<ReplayData>() {
                let list = sequence.borrow_mut().materialize(py)?.unbind();
                values.set_item("replay_data", list)?;
            }
        }
        self.storage = None;
        Ok(values)
    }
}

#[pymethods]
impl Replay {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(args: &Bound<'_, PyTuple>, kwargs: Option<&Bound<'_, PyDict>>) -> Self {
        let _ = (args, kwargs);
        Self {
            storage: None,
            values: None,
            header_dirty: false,
        }
    }
    #[getter]
    fn mode<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "mode")
    }
    #[getter]
    fn game_version<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "game_version")
    }
    #[getter]
    fn beatmap_hash<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "beatmap_hash")
    }
    #[getter]
    fn username<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "username")
    }
    #[getter]
    fn replay_hash<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "replay_hash")
    }
    #[getter]
    fn count_300<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "count_300")
    }
    #[getter]
    fn count_100<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "count_100")
    }
    #[getter]
    fn count_50<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "count_50")
    }
    #[getter]
    fn count_geki<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "count_geki")
    }
    #[getter]
    fn count_katu<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "count_katu")
    }
    #[getter]
    fn count_miss<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "count_miss")
    }
    #[getter]
    fn score<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "score")
    }
    #[getter]
    fn max_combo<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "max_combo")
    }
    #[getter]
    fn perfect<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "perfect")
    }
    #[getter]
    fn mods<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "mods")
    }
    #[getter]
    fn life_bar_graph<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "life_bar_graph")
    }
    #[getter]
    fn timestamp<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "timestamp")
    }
    #[getter]
    fn replay_data<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "replay_data")
    }
    #[getter]
    fn replay_id<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "replay_id")
    }
    #[getter]
    fn rng_seed<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "rng_seed")
    }
    #[getter]
    fn __dict__<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        self.materialize(py)
    }
    fn _materialize(&mut self, py: Python<'_>) -> PyResult<()> {
        self.materialize(py)?;
        Ok(())
    }
    fn __getattr__<'py>(&mut self, py: Python<'py>, name: &str) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, name)
    }
    fn __setattr__(&mut self, py: Python<'_>, name: &str, value: Bound<'_, PyAny>) -> PyResult<()> {
        if name == "__dict__" {
            self.values = Some(value.cast_into::<PyDict>()?.unbind());
            self.storage = None;
        } else {
            if name != "replay_data" && FIELDS.contains(&name) {
                self.header_dirty = true;
            }
            self.values(py).set_item(name, value)?;
        }
        Ok(())
    }
    fn __delattr__(&mut self, py: Python<'_>, name: &str) -> PyResult<()> {
        self.materialize(py)?
            .del_item(name)
            .map_err(|_| PyAttributeError::new_err(name.to_owned()))
    }
    #[getter]
    fn _cached_field_count(&self, py: Python<'_>) -> usize {
        self.values
            .as_ref()
            .map_or(0, |values| values.bind(py).len())
    }
    #[getter]
    fn _cached_event_count(&self, py: Python<'_>) -> PyResult<usize> {
        if let Some(values) = &self.values {
            if let Some(data) = values.bind(py).get_item("replay_data")? {
                if let Ok(sequence) = data.cast::<ReplayData>() {
                    return sequence.getattr("_cached_event_count")?.extract();
                }
                return data.len();
            }
        }
        Ok(0)
    }
    fn __traverse__(&self, visit: pyo3::PyVisit<'_>) -> Result<(), pyo3::PyTraverseError> {
        visit.call(&self.values)
    }
    fn __clear__(&mut self) {
        self.values = None;
    }
}
