mod bindings;
mod codec;
mod events;
mod formatting;
mod models;
mod replay;
mod sequence;
mod storage;

use pyo3::prelude::*;

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<replay::Replay>()?;
    module.add_class::<sequence::ReplayData>()?;
    module.add_class::<models::ReplayEvent>()?;
    module.add_class::<models::ReplayEventOsu>()?;
    module.add_class::<models::ReplayEventTaiko>()?;
    module.add_class::<models::ReplayEventCatch>()?;
    module.add_class::<models::ReplayEventMania>()?;
    module.add_function(wrap_pyfunction!(bindings::unpack, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::unpack_timestamp, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::parse_events, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::parse_replay_data, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::pack, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::_format_float, module)?)?;
    Ok(())
}
