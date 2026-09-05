mod bindings;
mod codec;

use pyo3::prelude::*;

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(bindings::unpack, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::unpack_timestamp, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::parse_events, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::parse_replay_data, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::pack, module)?)?;
    Ok(())
}
