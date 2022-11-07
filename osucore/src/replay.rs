use crate::flags::Mod;
use crate::game_mode::GameMode;
use crate::life_bar_state::LifeBarState;
use crate::replay_events::{ReplayEventCatch, ReplayEventMania, ReplayEventOsu, ReplayEventTaiko};
use pyo3::prelude::*;

#[pymethods]
impl Replay {
    fn __str__(&self) -> PyResult<String> {
        Ok(format!("{:?}", self))
    }
    fn __repr__(&self) -> String {
        format!("{:?}", self)
    }
}

#[derive(Debug)]
#[pyclass]
pub struct Replay {
    #[pyo3(get, set)]
    pub mode: GameMode,
    #[pyo3(get, set)]
    pub game_version: i32,
    #[pyo3(get, set)]
    pub beatmap_hash: Option<String>,
    #[pyo3(get, set)]
    pub username: Option<String>,
    #[pyo3(get, set)]
    pub replay_hash: Option<String>,
    #[pyo3(get, set)]
    pub count_300: i16,
    #[pyo3(get, set)]
    pub count_100: i16,
    #[pyo3(get, set)]
    pub count_50: i16,
    #[pyo3(get, set)]
    pub count_geki: i16,
    #[pyo3(get, set)]
    pub count_katu: i16,
    #[pyo3(get, set)]
    pub count_miss: i16,
    #[pyo3(get, set)]
    pub score: i32,
    #[pyo3(get, set)]
    pub max_combo: i16,
    #[pyo3(get, set)]
    pub perfect: bool,
    #[pyo3(get, set)]
    pub mods: Mod,
    #[pyo3(get, set)]
    pub life_bar_graph: Option<Vec<LifeBarState>>,
    #[pyo3(get, set)]
    pub timestamp: i64,
    #[pyo3(get, set)]
    pub replay_data: ReplayDataContainer,
    #[pyo3(get, set)]
    pub rng_seed: Option<i32>,
    #[pyo3(get, set)]
    pub replay_id: u64,
}

#[derive(Debug, Clone, Default)]
#[pyclass]
pub struct ReplayDataContainer {
    #[pyo3(get, set)]
    pub osu_replay_data: Option<Vec<ReplayEventOsu>>,
    #[pyo3(get, set)]
    pub taiko_replay_data: Option<Vec<ReplayEventTaiko>>,
    #[pyo3(get, set)]
    pub catch_replay_data: Option<Vec<ReplayEventCatch>>,
    #[pyo3(get, set)]
    pub mania_replay_data: Option<Vec<ReplayEventMania>>,
}

impl From<Vec<ReplayEventOsu>> for ReplayDataContainer {
    fn from(data: Vec<ReplayEventOsu>) -> Self {
        ReplayDataContainer {
            osu_replay_data: Some(data),
            taiko_replay_data: None,
            catch_replay_data: None,
            mania_replay_data: None,
        }
    }
}

impl From<Vec<ReplayEventTaiko>> for ReplayDataContainer {
    fn from(data: Vec<ReplayEventTaiko>) -> Self {
        ReplayDataContainer {
            osu_replay_data: None,
            taiko_replay_data: Some(data),
            catch_replay_data: None,
            mania_replay_data: None,
        }
    }
}

impl From<Vec<ReplayEventCatch>> for ReplayDataContainer {
    fn from(data: Vec<ReplayEventCatch>) -> Self {
        ReplayDataContainer {
            osu_replay_data: None,
            taiko_replay_data: None,
            catch_replay_data: Some(data),
            mania_replay_data: None,
        }
    }
}

impl From<Vec<ReplayEventMania>> for ReplayDataContainer {
    fn from(data: Vec<ReplayEventMania>) -> Self {
        ReplayDataContainer {
            osu_replay_data: None,
            taiko_replay_data: None,
            catch_replay_data: None,
            mania_replay_data: Some(data),
        }
    }
}

pub struct RngSeed(pub i32);
