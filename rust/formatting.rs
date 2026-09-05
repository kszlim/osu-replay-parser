//! Python-compatible numeric text without allocating Python numbers.

use crate::events::Frame;
use std::fmt::Write;

pub fn float(output: &mut String, value: f64) {
    use lexical_write_float::{NumberFormatBuilder, Options, ToLexicalWithOptions};
    use std::num::NonZeroI32;

    const FORMAT: u128 = NumberFormatBuilder::new()
        .required_exponent_sign(true)
        .build_strict();
    const OPTIONS: Options = Options::builder()
        .positive_exponent_break(NonZeroI32::new(15))
        .negative_exponent_break(NonZeroI32::new(-4))
        .build_strict();
    // Python suppresses NaN's sign and uses lowercase spelling.
    if value.is_nan() {
        output.push_str("nan");
        return;
    }
    let mut buffer = [0u8; lexical_write_float::BUFFER_SIZE];
    let bytes = value.to_lexical_with_options::<FORMAT>(&mut buffer, &OPTIONS);
    let text = std::str::from_utf8(bytes).expect("lexical emits ASCII");
    if let Some((mantissa, exponent)) = text.split_once('e') {
        // Python omits an integral mantissa's .0 in scientific notation and
        // pads exponents to at least two digits. Lexical handles the conversion.
        output.push_str(mantissa.strip_suffix(".0").unwrap_or(mantissa));
        output.push('e');
        output.push_str(&exponent[..1]);
        if exponent.len() == 2 {
            output.push('0');
        }
        output.push_str(&exponent[1..]);
    } else {
        output.push_str(text);
    }
}

pub fn key_value(value: i64, bits: u32) -> u64 {
    if value >= 0 {
        return value as u64;
    }
    let boundary = 1i128 << bits;
    let base = if i128::from(value) >= -boundary {
        boundary
    } else {
        1i128 << (64 - value.unsigned_abs().leading_zeros())
    };
    (base + i128::from(value)) as u64
}

fn encoded_key(value: i64, bits: u32, legacy: bool) -> i128 {
    if legacy {
        i128::from(value)
    } else {
        i128::from(key_value(value, bits))
    }
}

pub fn frame(output: &mut String, frame: Frame, legacy_flags: bool) {
    match frame {
        Frame::Base { .. } => (),
        Frame::Osu { time, x, y, keys } => {
            write!(output, "{time}|").expect("writing to String cannot fail");
            float(output, x);
            output.push('|');
            float(output, y);
            write!(output, "|{},", encoded_key(keys, 5, legacy_flags))
                .expect("writing to String cannot fail");
        }
        Frame::Taiko { time, x, keys } => {
            write!(
                output,
                "{time}|{x}|0|{},",
                encoded_key(keys, 4, legacy_flags)
            )
            .expect("writing to String cannot fail");
        }
        Frame::Catch { time, x, dashing } => {
            write!(output, "{time}|").expect("writing to String cannot fail");
            float(output, x);
            write!(output, "|0|{},", u8::from(dashing)).expect("writing to String cannot fail");
        }
        Frame::Mania { time, keys } => {
            write!(
                output,
                "{time}|{}|0|0,",
                encoded_key(keys, 18, legacy_flags)
            )
            .expect("writing to String cannot fail");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn python_float_boundaries() {
        for (value, expected) in [
            (0.0, "0.0"),
            (-0.0, "-0.0"),
            (1e-4, "0.0001"),
            (1e-5, "1e-05"),
            (1e16, "1e+16"),
            (f64::from_bits(1), "5e-324"),
            (f64::INFINITY, "inf"),
        ] {
            let mut text = String::new();
            float(&mut text, value);
            assert_eq!(text, expected);
        }
    }
    #[test]
    fn negative_flags_follow_python_boundaries() {
        assert_eq!(key_value(-1, 5), 31);
        assert_eq!(key_value(-32, 5), 0);
        assert_eq!(key_value(-33, 5), 31);
        assert_eq!(key_value(-64, 5), 64);
        assert_eq!(key_value(i64::MIN, 5), 1 << 63);
    }
}
