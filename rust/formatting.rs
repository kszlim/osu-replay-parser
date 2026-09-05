//! Python-compatible numeric text without allocating Python numbers.

use crate::events::Frame;
use std::fmt::Write;

pub fn float(output: &mut String, value: f64) {
    if value.is_nan() {
        output.push_str("nan");
        return;
    }
    if value.is_infinite() {
        output.push_str(if value.is_sign_negative() {
            "-inf"
        } else {
            "inf"
        });
        return;
    }
    if value == 0.0 {
        output.push_str(if value.is_sign_negative() {
            "-0.0"
        } else {
            "0.0"
        });
        return;
    }
    if value.is_sign_negative() {
        output.push('-');
    }
    let mut buffer = ryu::Buffer::new();
    let text = buffer.format_finite(value.abs());
    let (mantissa, explicit) = match text.split_once('e') {
        Some((mantissa, exponent)) => (
            mantissa,
            exponent
                .parse::<i32>()
                .expect("Ryu emits a decimal exponent"),
        ),
        None => (text, 0),
    };
    let decimal = mantissa.find('.').unwrap_or(mantissa.len());
    let mut digits = [0u8; 32];
    let mut length = 0;
    for byte in mantissa.bytes().filter(|byte| *byte != b'.') {
        digits[length] = byte;
        length += 1;
    }
    let first = digits[..length]
        .iter()
        .position(|byte| *byte != b'0')
        .expect("nonzero float has a significant digit");
    let last = digits[..length]
        .iter()
        .rposition(|byte| *byte != b'0')
        .unwrap()
        + 1;
    let exponent = explicit + decimal as i32 - first as i32 - 1;
    let digits = std::str::from_utf8(&digits[first..last]).expect("Ryu emits ASCII digits");
    if !(-4..16).contains(&exponent) {
        output.push_str(&digits[..1]);
        if digits.len() > 1 {
            output.push('.');
            output.push_str(&digits[1..]);
        }
        write!(output, "e{exponent:+03}").expect("writing to String cannot fail");
    } else if exponent < 0 {
        output.push_str("0.");
        for _ in 0..(-exponent - 1) {
            output.push('0');
        }
        output.push_str(digits);
    } else {
        let point = exponent as usize + 1;
        if point >= digits.len() {
            output.push_str(digits);
            for _ in digits.len()..point {
                output.push('0');
            }
            output.push_str(".0");
        } else {
            output.push_str(&digits[..point]);
            output.push('.');
            output.push_str(&digits[point..]);
        }
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
