use nom::bytes::complete::take;
use nom::number::complete::{i16, i32, i64, i8, u8};
use nom::IResult;
use nom_leb128::leb128_u128;

use nom::combinator::map;

use fast_float::parse;
use nom::branch::alt;

use crate::config::ParseConfig;
use crate::flags::Mod;
use crate::game_mode::GameMode;
use crate::life_bar_state::LifeBarState;
use crate::replay::RngSeed;
use crate::replay::{Replay, ReplayDataContainer};
use crate::replay_events::{
    ByteSlices, ReplayEvent, ReplayEventCatch, ReplayEventMania, ReplayEventOsu, ReplayEventTaiko,
};

use xz2::stream::{Action, Stream};

type ParseResult<'a, T> = IResult<&'a [u8], T>;

fn parse_string<'a>(input: &'a [u8], context: &'a str) -> ParseResult<'a, Option<String>> {
    let (input, byte) = u8(input).map(|(input, byte)| {
        if byte != 0x00 && byte != 0x0b {
            panic!(
                "Expected the first byte of a string to be 0x00 or 0x0b, but got, {:?}, {:?}",
                byte, context
            );
        };
        (input, byte)
    })?;
    if byte == 0x0b {
        let (input, string) = leb128_u128(input).and_then(|(input, string_length)| {
            take(usize::try_from(string_length).unwrap())(input).map(|(input, string_bytes)| {
                (
                    input,
                    Some(String::from_utf8(string_bytes.to_vec()).unwrap()),
                )
            })
        })?;
        ParseResult::Ok((input, string))
    } else {
        ParseResult::Ok((input, None))
    }
}

fn parse_life_bar_graph(input: &[u8]) -> ParseResult<Option<Vec<LifeBarState>>> {
    let (input, string) = parse_string(input, "parse_life_bar_graph")?;
    let result = string.map(|life_bar| {
        let result: Vec<LifeBarState> = life_bar
            .split(',')
            .flat_map(|string| string.split_once('|'))
            .map(|(time, life)| {
                let time = time.parse::<u32>().unwrap();
                let life = parse(life).unwrap();
                LifeBarState { time, life }
            })
            .collect();
        result
    });
    match result {
        Some(life_bar_states) if life_bar_states.is_empty() => ParseResult::Ok((input, None)),
        result @ Some(_) => ParseResult::Ok((input, result)),
        None => ParseResult::Ok((input, None)),
    }
}

fn parse_replay_data<'a, 'b, T: for<'c> TryFrom<ByteSlices<'c>> + ReplayEvent + Clone>(
    input: &'a [u8],
    parse_config: &'b ParseConfig,
) -> ParseResult<'a, (Option<Vec<T>>, Option<RngSeed>)> {
    let (input, replay_length) = i32(parse_config.byte_order)(input)?;
    let (input, replay_data) = take(usize::try_from(replay_length).unwrap())(input)?;
    if parse_config.header_only {
        ParseResult::Ok((input, (None, None)))
    } else {
        let mut data = Vec::with_capacity(1024 * 1024);
        let mut stream = Stream::new_lzma_decoder(1024 * 1024 * 5).unwrap();
        stream
            .process_vec(replay_data, &mut data, Action::Run)
            .unwrap();
        let (replay_events, rng_seed) = parse_replay_string(data);
        ParseResult::Ok((input, (Some(replay_events.to_vec()), rng_seed)))
    }
}

pub fn parse_replay_string<T: for<'a> TryFrom<ByteSlices<'a>> + ReplayEvent>(
    replay_data: Vec<u8>,
) -> (Vec<T>, Option<RngSeed>) {
    let splits = replay_data.split(|&s| s == b',');

    let mut has_trailing_comma = false;
    if let Some(last) = splits.clone().last() {
        has_trailing_comma = last == b"";
    }
    let last_elem = if has_trailing_comma { 1 } else { 0 };
    let splits = splits.map(|bytes| bytes.split(|&byte| byte == b'|'));
    let rng_seed: Option<i32> = splits
        .clone()
        .rev()
        .nth(last_elem)
        .and_then(|mut bytes| bytes.nth(3).and_then(|bytes| atoi::atoi(bytes)));
    let mut events: Vec<T> = splits
        .flat_map(|event| T::try_from(event.collect::<Vec<_>>()).ok())
        .collect();
    let last = events.pop().unwrap();
    if last.is_magic_number() && rng_seed.is_some() {
        (events, rng_seed.map(|int| RngSeed(int)))
    } else {
        events.push(last);
        (events, None)
    }
}

fn parse_replay_id<'a, 'b>(input: &'a [u8], parse_config: &'b ParseConfig) -> ParseResult<'a, u64> {
    let i64_parser = map(i64(parse_config.byte_order), |int| int as u64);
    let i32_parser = map(i32(parse_config.byte_order), |int| int as u64);
    ParseResult::Ok(alt((i64_parser, i32_parser))(input)?)
}

pub fn osr_parser<'a>(
    input: &'a [u8],
    parse_config: Option<ParseConfig>,
) -> ParseResult<'a, Replay> {
    let parse_config = parse_config.unwrap_or_default();
    let (input, game_mode) =
        i8(input).map(|(input, game_mode)| (input, GameMode::from(game_mode)))?;
    let (input, game_version) = i32(parse_config.byte_order)(input)?;
    let (input, beatmap_hash) = parse_string(input, "beatmap_hash")?;
    let (input, username) = parse_string(input, "username")?;
    let (input, replay_hash) = parse_string(input, "replay_hash")?;
    let (input, count_300) = i16(parse_config.byte_order)(input)?;
    let (input, count_100) = i16(parse_config.byte_order)(input)?;
    let (input, count_50) = i16(parse_config.byte_order)(input)?;
    let (input, count_geki) = i16(parse_config.byte_order)(input)?;
    let (input, count_katu) = i16(parse_config.byte_order)(input)?;
    let (input, count_miss) = i16(parse_config.byte_order)(input)?;
    let (input, score) = i32(parse_config.byte_order)(input)?;
    let (input, max_combo) = i16(parse_config.byte_order)(input)?;
    let (input, perfect) = u8(input).map(|(input, byte)| (input, byte == 1))?;
    let (input, mods) =
        i32(parse_config.byte_order)(input).map(|(input, int)| (input, Mod::from(int)))?;
    let (input, life_bar_graph) = parse_life_bar_graph(input)?;
    let (data_input, timestamp) = i64(parse_config.byte_order)(input)?;
    let rng_seed;
    let mut std_data = None;
    let mut taiko_data = None;
    let mut catch_data = None;
    let mut mania_data = None;
    let mut replay_data_container = ReplayDataContainer::default();
    let input;
    match game_mode {
        GameMode::STD => {
            (input, (std_data, rng_seed)) =
                parse_replay_data::<ReplayEventOsu>(data_input, &parse_config)?;
        }
        GameMode::TAIKO => {
            (input, (taiko_data, rng_seed)) =
                parse_replay_data::<ReplayEventTaiko>(data_input, &parse_config)?;
        }
        GameMode::CTB => {
            (input, (catch_data, rng_seed)) =
                parse_replay_data::<ReplayEventCatch>(data_input, &parse_config)?;
        }
        GameMode::MANIA => {
            (input, (mania_data, rng_seed)) =
                parse_replay_data::<ReplayEventMania>(data_input, &parse_config)?;
        }
        GameMode::UNKNOWN => panic!("Unknown GameMode"),
    }
    if let Some(std_data) = std_data {
        replay_data_container = std_data.into()
    };
    if let Some(taiko_data) = taiko_data {
        replay_data_container = taiko_data.into()
    };
    if let Some(catch_data) = catch_data {
        replay_data_container = catch_data.into()
    };
    if let Some(mania_data) = mania_data {
        replay_data_container = mania_data.into()
    };
    let (input, replay_id) = parse_replay_id(input, &parse_config)?;
    let replay = Replay {
        mode: game_mode,
        game_version,
        beatmap_hash,
        username,
        replay_hash,
        count_300,
        count_100,
        count_50,
        count_geki,
        count_katu,
        count_miss,
        score,
        max_combo,
        perfect,
        mods,
        life_bar_graph,
        timestamp,
        replay_data: replay_data_container,
        rng_seed: rng_seed.map(|seed| seed.0),
        replay_id,
    };
    ParseResult::Ok((input, replay))
}
