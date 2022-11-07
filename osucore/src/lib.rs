use std::fs;

use pyo3::prelude::*;

pub mod config;
pub mod flags;
pub mod game_mode;
pub mod life_bar_state;
mod parser;
pub mod replay;
pub mod replay_events;

use crate::config::ParseConfig;
use crate::flags::{Key, KeyMania, KeyTaiko, Mod};
use crate::game_mode::GameMode;
use crate::life_bar_state::LifeBarState;
use crate::parser::{osr_parser, parse_replay_string};
use crate::replay::{Replay, ReplayDataContainer};
use crate::replay_events::{ReplayEventCatch, ReplayEventMania, ReplayEventOsu, ReplayEventTaiko};

use mimalloc::MiMalloc;
#[global_allocator]
static GLOBAL: MiMalloc = MiMalloc;

use rayon::prelude::*;

pub fn replay_from_bytes(data: &[u8], parse_config: Option<ParseConfig>) -> Replay {
    osr_parser(data, parse_config).unwrap().1
}

pub fn replay_from_path<T: AsRef<str>>(path: T, parse_config: Option<ParseConfig>) -> Replay {
    let data = fs::read(path.as_ref()).unwrap();
    replay_from_bytes(&data, parse_config)
}

pub fn replays_from_paths<T: AsRef<str> + Send + Sync>(
    paths: &[T],
    parse_config: Option<ParseConfig>,
) -> Vec<Replay> {
    paths
        .par_iter()
        .map(|path| replay_from_path(path, parse_config))
        .collect()
}

#[pyfunction("/", header_only = false)]
fn parse_replay_from_bytes(data: &[u8], header_only: bool) -> Replay {
    replay_from_bytes(data, Some(ParseConfig::new(header_only)))
}

#[pyfunction("/", header_only = false)]
fn parse_replay_from_path(path: &str, header_only: bool) -> Replay {
    replay_from_path(path, Some(ParseConfig::new(header_only)))
}

#[pyfunction("/", header_only = false)]
fn parse_replays_from_paths(paths: Vec<&str>, header_only: bool) -> Vec<Replay> {
    replays_from_paths(&paths, Some(ParseConfig::new(header_only)))
}

#[pyfunction]
fn parse_replay_data(data: &[u8], mode: GameMode) -> ReplayDataContainer {
    match mode {
        GameMode::STD => parse_replay_string::<ReplayEventOsu>(data.to_vec())
            .0
            .into(),
        GameMode::TAIKO => parse_replay_string::<ReplayEventTaiko>(data.to_vec())
            .0
            .into(),
        GameMode::CTB => parse_replay_string::<ReplayEventCatch>(data.to_vec())
            .0
            .into(),
        GameMode::MANIA => parse_replay_string::<ReplayEventMania>(data.to_vec())
            .0
            .into(),
        _ => parse_replay_string::<ReplayEventOsu>(data.to_vec())
            .0
            .into(),
    }
}

#[pymodule]
fn osucore(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<Replay>()?;
    m.add_class::<ReplayEventOsu>()?;
    m.add_class::<ReplayEventTaiko>()?;
    m.add_class::<ReplayEventCatch>()?;
    m.add_class::<ReplayEventMania>()?;
    m.add_class::<LifeBarState>()?;
    m.add_class::<Mod>()?;
    m.add_class::<GameMode>()?;
    m.add_class::<Key>()?;
    m.add_class::<KeyTaiko>()?;
    m.add_class::<KeyMania>()?;

    m.add_function(wrap_pyfunction!(parse_replay_from_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(parse_replay_from_path, m)?)?;
    m.add_function(wrap_pyfunction!(parse_replays_from_paths, m)?)?;
    m.add_function(wrap_pyfunction!(parse_replay_data, m)?)?;

    Ok(())
}

#[cfg(test)]
mod tests {}
