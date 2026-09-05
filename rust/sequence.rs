//! Lazy Python sequence over Rust-owned frames. Indexed views are cached so
//! references and edits stay live. Structural edits promote to a real list.

use crate::{events::Frame, models};
use pyo3::class::basic::CompareOp;
use pyo3::exceptions::{PyIndexError, PyStopIteration, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyList, PySlice};
use std::{collections::HashMap, sync::Arc};

#[pyclass(module = "osrparse", weakref)]
pub struct ReplayData {
    pub frames: Arc<Vec<Frame>>,
    pub cache: HashMap<usize, Py<PyAny>>,
    pub materialized: Option<Py<PyList>>,
    keys: HashMap<(u8, i64), Py<PyAny>>,
}

impl ReplayData {
    pub fn from_frames(frames: Arc<Vec<Frame>>) -> Self {
        Self {
            frames,
            cache: HashMap::new(),
            materialized: None,
            keys: HashMap::new(),
        }
    }

    pub fn from_list(list: Py<PyList>) -> Self {
        let mut data = Self::from_frames(Arc::new(Vec::new()));
        data.materialized = Some(list);
        data
    }

    pub fn length(&self, py: Python<'_>) -> usize {
        self.materialized
            .as_ref()
            .map_or(self.frames.len(), |list| list.bind(py).len())
    }

    pub fn item(&mut self, py: Python<'_>, index: usize) -> PyResult<Py<PyAny>> {
        if let Some(list) = &self.materialized {
            return Ok(list.bind(py).get_item(index)?.unbind());
        }
        if let Some(value) = self.cache.get(&index) {
            return Ok(value.clone_ref(py));
        }
        let frame = *self
            .frames
            .get(index)
            .ok_or_else(|| PyIndexError::new_err("list index out of range"))?;
        let keys = if let Some(mask) = frame.keys() {
            let (kind, name) = match frame {
                Frame::Osu { .. } => (0, "Key"),
                Frame::Taiko { .. } => (1, "KeyTaiko"),
                _ => (3, "KeyMania"),
            };
            let member = match self.keys.entry((kind, mask)) {
                std::collections::hash_map::Entry::Occupied(entry) => entry.into_mut(),
                std::collections::hash_map::Entry::Vacant(entry) => entry.insert(
                    py.import("osrparse.utils")?
                        .getattr(name)?
                        .call1((mask,))?
                        .unbind(),
                ),
            };
            Some(member.clone_ref(py))
        } else {
            None
        };
        let value = models::into_python(py, frame, keys)?;
        self.cache.insert(index, value.clone_ref(py));
        Ok(value)
    }

    pub fn materialize<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        if let Some(list) = &self.materialized {
            return Ok(list.bind(py).clone());
        }
        let mut items = Vec::with_capacity(self.frames.len());
        for index in 0..self.frames.len() {
            items.push(self.item(py, index)?);
        }
        let list = PyList::new(py, items)?;
        self.materialized = Some(list.clone().unbind());
        self.cache.clear();
        self.keys.clear();
        // Existing views own their scalar data and remain valid after edits.
        self.frames = Arc::new(Vec::new());
        Ok(list)
    }
}

fn list<'py>(slf: &Bound<'py, ReplayData>) -> PyResult<Bound<'py, PyList>> {
    let result = slf.borrow_mut().materialize(slf.py())?.unbind();
    Ok(result.into_bound(slf.py()))
}

#[pymethods]
impl ReplayData {
    #[new]
    #[pyo3(signature = (items: "Iterable[ReplayEvent] | None"=None))]
    fn new(py: Python<'_>, items: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let values = match items {
            Some(items) => PyList::new(py, items.try_iter()?.collect::<PyResult<Vec<_>>>()?)?,
            None => PyList::empty(py),
        };
        Ok(Self::from_list(values.unbind()))
    }

    fn __len__(&self, py: Python<'_>) -> usize {
        self.length(py)
    }

    fn __getitem__(slf: &Bound<'_, Self>, index: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let indexer = py.import("operator")?.getattr("index")?;
        if let Ok(slice) = index.cast::<PySlice>() {
            // Index conversion can call Python and mutate this sequence. Do it
            // before borrowing storage or capturing the current length.
            let convert = |name| -> PyResult<Bound<'_, PyAny>> {
                let value = slice.getattr(name)?;
                if value.is_none() {
                    Ok(value)
                } else {
                    indexer.call1((value,))
                }
            };
            let step = convert("step")?;
            if step.eq(0)? {
                return Err(PyValueError::new_err("slice step cannot be zero"));
            }
            let normalized =
                py.get_type::<PySlice>()
                    .call1((convert("start")?, convert("stop")?, step))?;
            let indices = normalized
                .cast::<PySlice>()?
                .indices(slf.borrow().length(py) as isize)?;
            let mut values = Vec::with_capacity(indices.slicelength);
            for n in 0..indices.slicelength {
                values.push(
                    slf.borrow_mut()
                        .item(py, (indices.start + n as isize * indices.step) as usize)?,
                );
            }
            return Ok(PyList::new(py, values)?.into_any().unbind());
        }
        let index: isize = indexer
            .call1((index,))?
            .extract()
            .map_err(|_| PyIndexError::new_err("cannot fit integer into an index-sized integer"))?;
        let length = slf.borrow().length(py) as isize;
        let index = if index < 0 { length + index } else { index };
        if !(0..length).contains(&index) {
            return Err(PyIndexError::new_err("list index out of range"));
        }
        slf.borrow_mut().item(py, index as usize)
    }

    fn __iter__(slf: Py<Self>, py: Python<'_>) -> PyResult<Py<ReplayDataIterator>> {
        Py::new(
            py,
            ReplayDataIterator {
                sequence: Some(slf),
                index: 0,
            },
        )
    }

    fn __setitem__(
        slf: &Bound<'_, Self>,
        index: &Bound<'_, PyAny>,
        value: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        list(slf)?.call_method1("__setitem__", (index, value))?;
        Ok(())
    }
    fn __delitem__(slf: &Bound<'_, Self>, index: &Bound<'_, PyAny>) -> PyResult<()> {
        list(slf)?.call_method1("__delitem__", (index,))?;
        Ok(())
    }
    #[pyo3(signature = (value: "ReplayEvent"))]
    fn append(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        list(slf)?.append(value)
    }
    #[pyo3(signature = (values: "Iterable[ReplayEvent]"))]
    fn extend(slf: &Bound<'_, Self>, values: &Bound<'_, PyAny>) -> PyResult<()> {
        list(slf)?.call_method1("extend", (values,))?;
        Ok(())
    }
    #[pyo3(signature = (index, value: "ReplayEvent"))]
    fn insert(slf: &Bound<'_, Self>, index: isize, value: &Bound<'_, PyAny>) -> PyResult<()> {
        list(slf)?.call_method1("insert", (index, value))?;
        Ok(())
    }
    #[pyo3(signature = (index=-1) -> "ReplayEvent")]
    fn pop(slf: &Bound<'_, Self>, index: isize) -> PyResult<Py<PyAny>> {
        Ok(list(slf)?.call_method1("pop", (index,))?.unbind())
    }
    #[pyo3(signature = (value: "ReplayEvent"))]
    fn remove(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        list(slf)?.call_method1("remove", (value,))?;
        Ok(())
    }
    fn clear(slf: &Bound<'_, Self>) -> PyResult<()> {
        let (items, cached, keys) = {
            let mut data = slf.borrow_mut();
            let items = data
                .materialized
                .get_or_insert_with(|| PyList::empty(slf.py()).unbind())
                .clone_ref(slf.py());
            data.frames = Arc::new(Vec::new());
            (
                items,
                std::mem::take(&mut data.cache),
                std::mem::take(&mut data.keys),
            )
        };
        // Dropping objects may run Python finalizers that re-enter this object.
        items.bind(slf.py()).call_method0("clear")?;
        drop((cached, keys));
        Ok(())
    }
    fn reverse(slf: &Bound<'_, Self>) -> PyResult<()> {
        list(slf)?.call_method0("reverse")?;
        Ok(())
    }
    #[pyo3(signature = (*, key: "Callable[[ReplayEvent], Any] | None"=None, reverse=false))]
    fn sort(slf: &Bound<'_, Self>, key: Option<&Bound<'_, PyAny>>, reverse: bool) -> PyResult<()> {
        let kwargs = pyo3::types::PyDict::new(slf.py());
        kwargs.set_item("key", key)?;
        kwargs.set_item("reverse", reverse)?;
        list(slf)?.call_method("sort", (), Some(&kwargs))?;
        Ok(())
    }
    #[pyo3(signature = (value: "ReplayEvent"))]
    fn count(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<usize> {
        list(slf)?.call_method1("count", (value,))?.extract()
    }
    #[pyo3(signature = (value: "ReplayEvent", start=0, stop=None))]
    fn index(
        slf: &Bound<'_, Self>,
        value: &Bound<'_, PyAny>,
        start: isize,
        stop: Option<isize>,
    ) -> PyResult<usize> {
        let list = list(slf)?;
        match stop {
            Some(stop) => list.call_method1("index", (value, start, stop))?,
            None => list.call_method1("index", (value, start))?,
        }
        .extract()
    }
    fn __contains__(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<bool> {
        list(slf)?.contains(value)
    }
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        op: CompareOp,
    ) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        if slf.is(other) && matches!(op, CompareOp::Eq | CompareOp::Ne) {
            return Ok(matches!(op, CompareOp::Eq)
                .into_pyobject(py)?
                .to_owned()
                .into_any()
                .unbind());
        }
        let other = if let Ok(sequence) = other.cast::<Self>() {
            list(sequence)?.into_any()
        } else if other.is_instance_of::<PyList>() {
            other.clone()
        } else {
            return Ok(py.NotImplemented());
        };
        Ok(list(slf)?.rich_compare(other, op)?.unbind())
    }
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        Ok(list(slf)?.repr()?.to_str()?.to_owned())
    }
    #[pyo3(signature = () -> "list[ReplayEvent]")]
    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyList>> {
        Ok(list(slf)?
            .get_slice(0, slf.borrow().length(slf.py()))
            .unbind())
    }
    fn __copy__(slf: &Bound<'_, Self>) -> PyResult<Py<Self>> {
        Py::new(slf.py(), Self::new(slf.py(), Some(list(slf)?.as_any()))?)
    }
    fn __reduce__(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        Ok((slf.get_type(), (), list(slf)?)
            .into_pyobject(slf.py())?
            .into_any()
            .unbind())
    }
    fn __setstate__(&mut self, state: Bound<'_, PyList>) {
        self.frames = Arc::new(Vec::new());
        self.cache.clear();
        self.keys.clear();
        self.materialized = Some(state.unbind());
    }
    fn __iadd__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<()> {
        list(slf)?.call_method1("extend", (other,))?;
        Ok(())
    }
    fn __imul__(slf: &Bound<'_, Self>, count: &Bound<'_, PyAny>) -> PyResult<()> {
        list(slf)?.call_method1("__imul__", (count,))?;
        Ok(())
    }
    fn __add__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        let other = if let Ok(data) = other.cast::<Self>() {
            list(data)?.into_any()
        } else {
            other.clone()
        };
        Ok(list(slf)?.call_method1("__add__", (other,))?.unbind())
    }
    fn __radd__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        Ok(other.call_method1("__add__", (list(slf)?,))?.unbind())
    }
    fn __mul__(slf: &Bound<'_, Self>, count: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        Ok(list(slf)?.call_method1("__mul__", (count,))?.unbind())
    }
    fn __rmul__(slf: &Bound<'_, Self>, count: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        Self::__mul__(slf, count)
    }
    #[getter]
    fn _cached_event_count(&self, py: Python<'_>) -> usize {
        self.materialized
            .as_ref()
            .map_or(self.cache.len(), |list| list.bind(py).len())
    }
    fn __traverse__(&self, visit: pyo3::PyVisit<'_>) -> Result<(), pyo3::PyTraverseError> {
        visit.call(&self.materialized)?;
        for item in self.cache.values().chain(self.keys.values()) {
            visit.call(item)?;
        }
        Ok(())
    }
    fn __clear__(&mut self) {
        self.cache.clear();
        self.keys.clear();
        self.materialized = None;
    }
}

#[pyclass(module = "osrparse._native")]
pub struct ReplayDataIterator {
    sequence: Option<Py<ReplayData>>,
    index: usize,
}

#[pymethods]
impl ReplayDataIterator {
    fn __iter__(slf: Py<Self>) -> Py<Self> {
        slf
    }
    fn __next__(&mut self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let sequence = self
            .sequence
            .as_ref()
            .ok_or_else(|| PyStopIteration::new_err(()))?;
        let mut data = sequence.borrow_mut(py);
        if self.index >= data.length(py) {
            drop(data);
            self.sequence = None;
            return Err(PyStopIteration::new_err(()));
        }
        let item = data.item(py, self.index)?;
        self.index += 1;
        Ok(item)
    }
    fn __length_hint__(&self, py: Python<'_>) -> usize {
        self.sequence.as_ref().map_or(0, |sequence| {
            sequence.borrow(py).length(py).saturating_sub(self.index)
        })
    }
    fn __traverse__(&self, visit: pyo3::PyVisit<'_>) -> Result<(), pyo3::PyTraverseError> {
        visit.call(&self.sequence)
    }
    fn __clear__(&mut self) {
        self.sequence = None;
    }
}
