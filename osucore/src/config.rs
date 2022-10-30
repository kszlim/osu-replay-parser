use nom::number::Endianness;

#[derive(Clone, Copy)]
pub struct ParseConfig {
    pub byte_order: Endianness,
    pub header_only: bool,
}

impl ParseConfig {
    pub fn new(header_only: bool) -> ParseConfig {
        ParseConfig {
            byte_order: Endianness::Little,
            header_only,
        }
    }
}

impl Default for ParseConfig {
    fn default() -> ParseConfig {
        ParseConfig {
            byte_order: Endianness::Little,
            header_only: false,
        }
    }
}
