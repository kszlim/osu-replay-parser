use clap::{command, Parser};
use osucore::config::ParseConfig;
use osucore::replay_from_path;

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
    for _ in 0..5000 {
        let replays = replay_from_path(&cli.replay_paths[0], Some(parse_config));
    }
}
