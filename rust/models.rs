//! Native event classes. Scalars stay in Rust until requested by Python.
//! Accessing __dict__ or mutating an object promotes its fields to a normal
//! dictionary, preserving dataclass introspection and live dictionary edits.

use pyo3::exceptions::PyAttributeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFloat, PyInt, PyTuple};

use crate::events::Frame;

#[pyclass(subclass, weakref, module = "osrparse.utils")]
pub struct ReplayEvent {
    pub frame: Frame,
    pub keys: Option<Py<PyAny>>,
    state: Option<Py<PyDict>>,
}

impl ReplayEvent {
    pub fn from_frame(frame: Frame, keys: Option<Py<PyAny>>) -> Self {
        Self {
            frame,
            keys,
            state: None,
        }
    }

    fn field<'py>(&self, py: Python<'py>, name: &str) -> PyResult<Bound<'py, PyAny>> {
        if let Some(state) = &self.state {
            return state.bind(py).get_item(name)?.ok_or_else(|| missing(name));
        }
        match (name, self.frame) {
            ("time_delta", frame) => Ok(PyInt::new(py, frame.time()).into_any()),
            ("x", Frame::Osu { x, .. } | Frame::Catch { x, .. }) => {
                Ok(PyFloat::new(py, x).into_any())
            }
            ("x", Frame::Taiko { x, .. }) => Ok(PyInt::new(py, x).into_any()),
            ("y", Frame::Osu { y, .. }) => Ok(PyFloat::new(py, y).into_any()),
            ("keys", _) => self
                .keys
                .as_ref()
                .map(|keys| keys.bind(py).clone())
                .ok_or_else(|| missing(name)),
            ("dashing", Frame::Catch { dashing, .. }) => {
                Ok(dashing.into_pyobject(py)?.to_owned().into_any())
            }
            _ => Err(missing(name)),
        }
    }

    fn dictionary<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        if let Some(state) = &self.state {
            return Ok(state.bind(py).clone());
        }
        let state = PyDict::new(py);
        for field in self.frame.fields() {
            // Constructors leave fields for the generated Python initializer.
            if let Ok(value) = self.field(py, field) {
                state.set_item(field, value)?;
            }
        }
        self.state = Some(state.clone().unbind());
        Ok(state)
    }
}

fn missing(name: &str) -> PyErr {
    PyAttributeError::new_err(format!("no attribute {name:?}"))
}

#[pymethods]
impl ReplayEvent {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(args: &Bound<'_, PyTuple>, kwargs: Option<&Bound<'_, PyDict>>) -> Self {
        let _ = (args, kwargs);
        Self::from_frame(Frame::Base { time: 0 }, None)
    }

    #[getter]
    fn time_delta<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "time_delta")
    }
    #[getter]
    fn x<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "x")
    }
    #[getter]
    fn y<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "y")
    }
    #[getter]
    fn keys<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "keys")
    }
    #[getter]
    fn dashing<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, "dashing")
    }
    #[getter]
    fn __dict__<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        self.dictionary(py)
    }

    fn __getattr__<'py>(&self, py: Python<'py>, name: &str) -> PyResult<Bound<'py, PyAny>> {
        self.field(py, name)
    }

    fn __setattr__(&mut self, py: Python<'_>, name: &str, value: Bound<'_, PyAny>) -> PyResult<()> {
        if name == "__dict__" {
            self.state = Some(value.cast_into::<PyDict>()?.unbind());
            return Ok(());
        }
        self.dictionary(py)?.set_item(name, value)
    }

    fn __delattr__(&mut self, py: Python<'_>, name: &str) -> PyResult<()> {
        self.dictionary(py)?
            .del_item(name)
            .map_err(|_| missing(name))
    }

    fn __traverse__(&self, visit: pyo3::PyVisit<'_>) -> Result<(), pyo3::PyTraverseError> {
        visit.call(&self.keys)?;
        visit.call(&self.state)
    }

    fn __clear__(&mut self) {
        self.keys = None;
        self.state = None;
    }
}

macro_rules! event_class {
    ($name:ident, $default:expr) => {
        #[pyclass(extends = ReplayEvent, subclass, module = "osrparse.utils")]
        pub struct $name;

        #[pymethods]
        impl $name {
            #[new]
            #[pyo3(signature = (*args, **kwargs))]
            fn new(
                args: &Bound<'_, PyTuple>,
                kwargs: Option<&Bound<'_, PyDict>>,
            ) -> PyClassInitializer<Self> {
                let _ = (args, kwargs);
                PyClassInitializer::from(ReplayEvent::from_frame($default, None)).add_subclass(Self)
            }
        }
    };
}

event_class!(
    ReplayEventOsu,
    Frame::Osu {
        time: 0,
        x: 0.0,
        y: 0.0,
        keys: 0
    }
);
event_class!(
    ReplayEventTaiko,
    Frame::Taiko {
        time: 0,
        x: 0,
        keys: 0
    }
);
event_class!(
    ReplayEventCatch,
    Frame::Catch {
        time: 0,
        x: 0.0,
        dashing: false
    }
);
event_class!(ReplayEventMania, Frame::Mania { time: 0, keys: 0 });

pub fn into_python(py: Python<'_>, frame: Frame, keys: Option<Py<PyAny>>) -> PyResult<Py<PyAny>> {
    let event = ReplayEvent::from_frame(frame, keys);
    match frame {
        Frame::Base { .. } => Ok(Py::new(py, event)?.into_any()),
        Frame::Osu { .. } => Ok(Py::new(
            py,
            PyClassInitializer::from(event).add_subclass(ReplayEventOsu),
        )?
        .into_any()),
        Frame::Taiko { .. } => Ok(Py::new(
            py,
            PyClassInitializer::from(event).add_subclass(ReplayEventTaiko),
        )?
        .into_any()),
        Frame::Catch { .. } => Ok(Py::new(
            py,
            PyClassInitializer::from(event).add_subclass(ReplayEventCatch),
        )?
        .into_any()),
        Frame::Mania { .. } => Ok(Py::new(
            py,
            PyClassInitializer::from(event).add_subclass(ReplayEventMania),
        )?
        .into_any()),
    }
}
