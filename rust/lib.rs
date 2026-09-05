mod bindings;
mod codec;
mod events;
mod formatting;
mod models;
mod parse;
mod replay;
mod sequence;
mod storage;

#[pyo3::pymodule]
mod _native {
    #[pymodule_export]
    use crate::bindings::{_format_float, pack, parse_replay_data, unpack, unpack_timestamp};
    #[pymodule_export]
    use crate::models::{
        ReplayEvent, ReplayEventCatch, ReplayEventMania, ReplayEventOsu, ReplayEventTaiko,
    };
    #[pymodule_export]
    use crate::replay::Replay;
    #[pymodule_export]
    use crate::sequence::ReplayData;
}
