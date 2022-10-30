use clap::{command, Parser};
use osucore::config::ParseConfig;
use osucore::replays_from_paths;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Path to osr file to parse
    #[arg(short, long)]
    replay_paths: Vec<String>,

    /// Flag that skips parsing the osu replay play data
    #[arg(short, long)]
    header_only: bool,
}

fn main() {
    let cli = Cli::parse();
    let parse_config = ParseConfig::new(cli.header_only);
    let replays = replays_from_paths(&cli.replay_paths, Some(parse_config));
    for replay in replays {
        dbg!(replay);
    }
}
