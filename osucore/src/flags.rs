use pyo3::{prelude::*, pyclass::CompareOp};

#[derive(Debug, Clone, Copy, PartialEq, Hash)]
#[pyclass]
pub struct Key(pub i32);

#[derive(Clone, Debug, PartialEq, Hash)]
#[pyclass]
pub struct KeyTaiko(pub i32);

#[derive(Clone, Debug, PartialEq, Hash)]
#[pyclass]
pub struct KeyMania(pub i32);

#[derive(Default, Clone, Debug)]
#[pyclass]
pub struct Mod(pub u32);

const fn calculate_max(num_flags: u32, is_zero_indexed: bool) -> u64 {
    if is_zero_indexed {
        2u64.pow(num_flags - 2)
    } else {
        2u64.pow(num_flags - 1)
    }
}

#[pymethods]
impl KeyMania {
    #[classattr]
    const K1: KeyMania = KeyMania(1 << 0);

    #[classattr]
    const K2: KeyMania = KeyMania(1 << 1);

    #[classattr]
    const K3: KeyMania = KeyMania(1 << 2);

    #[classattr]
    const K4: KeyMania = KeyMania(1 << 3);

    #[classattr]
    const K5: KeyMania = KeyMania(1 << 4);

    #[classattr]
    const K6: KeyMania = KeyMania(1 << 5);

    #[classattr]
    const K7: KeyMania = KeyMania(1 << 6);

    #[classattr]
    const K8: KeyMania = KeyMania(1 << 7);

    #[classattr]
    const K9: KeyMania = KeyMania(1 << 8);

    #[classattr]
    const K10: KeyMania = KeyMania(1 << 9);

    #[classattr]
    const K11: KeyMania = KeyMania(1 << 10);

    #[classattr]
    const K12: KeyMania = KeyMania(1 << 11);

    #[classattr]
    const K13: KeyMania = KeyMania(1 << 12);

    #[classattr]
    const K14: KeyMania = KeyMania(1 << 13);

    #[classattr]
    const K15: KeyMania = KeyMania(1 << 14);

    #[classattr]
    const K16: KeyMania = KeyMania(1 << 15);

    #[classattr]
    const K17: KeyMania = KeyMania(1 << 16);

    #[classattr]
    const K18: KeyMania = KeyMania(1 << 17);

    #[getter]
    fn value(&self) -> i32 {
        IntFlag::value(self)
    }
    #[new]
    fn new(int: i32) -> KeyMania {
        KeyMania(int)
    }

    fn __xor__(&self, other: &Self) -> KeyMania {
        IntFlag::__xor__(self, other)
    }

    fn __rxor__(&self, other: &Self) -> KeyMania {
        IntFlag::__rxor__(self, other)
    }

    fn __or__(&self, other: &Self) -> KeyMania {
        IntFlag::__or__(self, other)
    }

    fn __ror__(&self, other: &Self) -> KeyMania {
        IntFlag::__ror__(self, other)
    }

    fn __and__(&self, other: &Self) -> KeyMania {
        IntFlag::__and__(self, other)
    }

    fn __add__(&self, other: &Self) -> i32 {
        IntFlag::__add__(self, other)
    }

    fn __sub__(&self, other: &Self) -> i32 {
        IntFlag::__sub__(self, other)
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        IntFlag::__richcmp__(self, other, op)
    }

    fn __repr__(&self) -> String {
        IntFlag::__repr__(self)
    }

    fn __int__(&self) -> i32 {
        IntFlag::__int__(self)
    }

    fn __bool__(&self) -> bool {
        IntFlag::__bool__(self)
    }
}

#[pymethods]
impl KeyTaiko {
    #[classattr]
    const LEFT_DON: KeyTaiko = KeyTaiko(1 << 0);

    #[classattr]
    const LEFT_KAT: KeyTaiko = KeyTaiko(1 << 1);

    #[classattr]
    const RIGHT_DON: KeyTaiko = KeyTaiko(1 << 2);

    #[classattr]
    const RIGHT_KAT: KeyTaiko = KeyTaiko(1 << 3);

    #[getter]
    fn value(&self) -> i32 {
        IntFlag::value(self)
    }
    #[new]
    fn new(int: i32) -> KeyTaiko {
        KeyTaiko(int)
    }

    fn __xor__(&self, other: &Self) -> KeyTaiko {
        IntFlag::__xor__(self, other)
    }

    fn __rxor__(&self, other: &Self) -> KeyTaiko {
        IntFlag::__rxor__(self, other)
    }

    fn __or__(&self, other: &Self) -> KeyTaiko {
        IntFlag::__or__(self, other)
    }

    fn __ror__(&self, other: &Self) -> KeyTaiko {
        IntFlag::__ror__(self, other)
    }

    fn __and__(&self, other: &Self) -> KeyTaiko {
        IntFlag::__and__(self, other)
    }

    fn __add__(&self, other: &Self) -> i32 {
        IntFlag::__add__(self, other)
    }

    fn __sub__(&self, other: &Self) -> i32 {
        IntFlag::__sub__(self, other)
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        IntFlag::__richcmp__(self, other, op)
    }

    fn __repr__(&self) -> String {
        IntFlag::__repr__(self)
    }

    fn __int__(&self) -> i32 {
        IntFlag::__int__(self)
    }

    fn __bool__(&self) -> bool {
        IntFlag::__bool__(self)
    }
}

#[pymethods]
impl Key {
    #[classattr]
    const M1: Key = Key(1 << 0);

    #[classattr]
    const M2: Key = Key(1 << 1);

    #[classattr]
    const K1: Key = Key(1 << 2);

    #[classattr]
    const K2: Key = Key(1 << 3);

    #[classattr]
    const SMOKE: Key = Key(1 << 4);

    #[getter]
    fn value(&self) -> i32 {
        IntFlag::value(self)
    }
    #[new]
    fn new(int: i32) -> Key {
        Key(int)
    }

    fn __xor__(&self, other: &Self) -> Key {
        IntFlag::__xor__(self, other)
    }

    fn __rxor__(&self, other: &Self) -> Key {
        IntFlag::__rxor__(self, other)
    }

    fn __or__(&self, other: &Self) -> Key {
        IntFlag::__or__(self, other)
    }

    fn __ror__(&self, other: &Self) -> Key {
        IntFlag::__ror__(self, other)
    }

    fn __and__(&self, other: &Self) -> Key {
        IntFlag::__and__(self, other)
    }

    fn __add__(&self, other: &Self) -> i32 {
        IntFlag::__add__(self, other)
    }

    fn __sub__(&self, other: &Self) -> i32 {
        IntFlag::__sub__(self, other)
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        IntFlag::__richcmp__(self, other, op)
    }

    fn __repr__(&self) -> String {
        IntFlag::__repr__(self)
    }

    fn __int__(&self) -> i32 {
        IntFlag::__int__(self)
    }

    fn __bool__(&self) -> bool {
        IntFlag::__bool__(self)
    }
}

#[pymethods]
#[allow(non_upper_case_globals)]
impl Mod {
    #[classattr]
    const NoMod: Mod = Mod(0);

    #[classattr]
    const NoFail: Mod = Mod(1 << 0);

    #[classattr]
    const Easy: Mod = Mod(1 << 1);

    #[classattr]
    const TouchDevice: Mod = Mod(1 << 2);

    #[classattr]
    const Hidden: Mod = Mod(1 << 3);

    #[classattr]
    const HardRock: Mod = Mod(1 << 4);

    #[classattr]
    const SuddenDeath: Mod = Mod(1 << 5);

    #[classattr]
    const DoubleTime: Mod = Mod(1 << 6);

    #[classattr]
    const Relax: Mod = Mod(1 << 7);

    #[classattr]
    const HalfTime: Mod = Mod(1 << 8);

    #[classattr]
    const Nightcore: Mod = Mod(1 << 9);

    #[classattr]
    const Flashlight: Mod = Mod(1 << 10);

    #[classattr]
    const Autoplay: Mod = Mod(1 << 11);

    #[classattr]
    const SpunOut: Mod = Mod(1 << 12);

    #[classattr]
    const Autopilot: Mod = Mod(1 << 13);

    #[classattr]
    const Perfect: Mod = Mod(1 << 14);

    #[classattr]
    const Key4: Mod = Mod(1 << 15);

    #[classattr]
    const Key5: Mod = Mod(1 << 16);

    #[classattr]
    const Key6: Mod = Mod(1 << 17);

    #[classattr]
    const Key7: Mod = Mod(1 << 18);

    #[classattr]
    const Key8: Mod = Mod(1 << 19);

    #[classattr]
    const FadeIn: Mod = Mod(1 << 20);

    #[classattr]
    const Random: Mod = Mod(1 << 21);

    #[classattr]
    const Cinema: Mod = Mod(1 << 22);

    #[classattr]
    const Target: Mod = Mod(1 << 23);

    #[classattr]
    const Key9: Mod = Mod(1 << 24);

    #[classattr]
    const KeyCoop: Mod = Mod(1 << 25);

    #[classattr]
    const Key1: Mod = Mod(1 << 26);

    #[classattr]
    const Key3: Mod = Mod(1 << 27);

    #[classattr]
    const Key2: Mod = Mod(1 << 28);

    #[classattr]
    const ScoreV2: Mod = Mod(1 << 29);

    #[classattr]
    const Mirror: Mod = Mod(1 << 30);

    #[getter]
    fn value(&self) -> i32 {
        IntFlag::value(self)
    }
    #[new]
    fn new(int: i32) -> Mod {
        Mod(int.try_into().unwrap())
    }

    fn __xor__(&self, other: &Self) -> Mod {
        IntFlag::__xor__(self, other)
    }

    fn __rxor__(&self, other: &Self) -> Mod {
        IntFlag::__rxor__(self, other)
    }

    fn __or__(&self, other: &Self) -> Mod {
        IntFlag::__or__(self, other)
    }

    fn __ror__(&self, other: &Self) -> Mod {
        IntFlag::__ror__(self, other)
    }

    fn __and__(&self, other: &Self) -> Mod {
        IntFlag::__and__(self, other)
    }

    fn __add__(&self, other: &Self) -> i32 {
        IntFlag::__add__(self, other)
    }

    fn __sub__(&self, other: &Self) -> i32 {
        IntFlag::__sub__(self, other)
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        IntFlag::__richcmp__(self, other, op)
    }

    fn __repr__(&self) -> String {
        IntFlag::__repr__(self)
    }

    fn __int__(&self) -> i32 {
        IntFlag::__int__(self)
    }

    fn __bool__(&self) -> bool {
        IntFlag::__bool__(self)
    }
}

trait IntFlag<const NUM_FLAGS: usize> {
    type FlagType;
    const NUM_FLAGS: usize = NUM_FLAGS;
    const FLAG_NAMES: [&'static str; NUM_FLAGS];
    const IS_ZERO_INDEXED_FLAGS: bool;
    const FLAG_MAX_VALUE: u64 = calculate_max(Self::NUM_FLAGS as u32, Self::IS_ZERO_INDEXED_FLAGS);
    fn value(&self) -> i32;
    fn new(int: i32) -> Self::FlagType;
    const NAME: &'static str;

    fn __xor__(&self, other: &Self) -> Self::FlagType {
        Self::new(self.value() ^ other.value())
    }

    fn __rxor__(&self, other: &Self) -> Self::FlagType {
        Self::new(self.value() ^ other.value())
    }

    fn __or__(&self, other: &Self) -> Self::FlagType {
        Self::new(self.value() + other.value())
    }

    fn __ror__(&self, other: &Self) -> Self::FlagType {
        Self::new(self.value() + other.value())
    }

    fn __and__(&self, other: &Self) -> Self::FlagType {
        Self::new(self.value() & other.value())
    }

    fn __add__(&self, other: &Self) -> i32 {
        self.value() + other.value()
    }

    fn __sub__(&self, other: &Self) -> i32 {
        self.value() - other.value()
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Lt => Ok(self.value() < other.value()),
            CompareOp::Le => Ok(self.value() <= other.value()),
            CompareOp::Eq => Ok(self.value() == other.value()),
            CompareOp::Ne => Ok(self.value() != other.value()),
            CompareOp::Gt => Ok(self.value() > other.value()),
            CompareOp::Ge => Ok(self.value() >= other.value()),
        }
    }

    fn __int__(&self) -> i32 {
        self.value()
    }

    fn __bool__(&self) -> bool {
        self.value() != 0
    }

    fn __repr__(&self) -> String {
        let mut data = String::with_capacity(6);
        data.push('<');
        data.extend(format!("{:}.", Self::NAME).chars());
        let mut max: u64 = Self::FLAG_MAX_VALUE;
        let mut index = 0;
        let mut flag_value: u64 = self.value() as u64;
        if flag_value == 0 && !Self::IS_ZERO_INDEXED_FLAGS {
            data.push('0');
        }
        while index < Self::NUM_FLAGS {
            if flag_value >= max {
                data.push_str(Self::FLAG_NAMES[Self::NUM_FLAGS - index - 1]);
                flag_value -= max;
                if flag_value == 0 {
                    break;
                }
                if flag_value >= 1 {
                    data.push('|');
                }
            }
            max /= 2;
            index += 1;
        }
        data.push_str(": ");
        data.push_str(&self.value().to_string());
        data.push('>');
        data
    }
}

impl IntFlag<32> for Mod {
    fn new(value: i32) -> Mod {
        Mod(value.try_into().unwrap())
    }

    type FlagType = Mod;

    fn value(&self) -> i32 {
        self.0.try_into().unwrap()
    }

    const FLAG_NAMES: [&'static str; Self::NUM_FLAGS] = [
        "NoMod",
        "NoFail",
        "Easy",
        "TouchDevice",
        "Hidden",
        "HardRock",
        "SuddenDeath",
        "DoubleTime",
        "Relax",
        "HalfTime",
        "Nightcore",
        "Flashlight",
        "Autoplay",
        "SpunOut",
        "Autopilot",
        "Perfect",
        "Key4",
        "Key5",
        "Key6",
        "Key7",
        "Key8",
        "FadeIn",
        "Random",
        "Cinema",
        "Target",
        "Key9",
        "KeyCoop",
        "Key1",
        "Key3",
        "Key2",
        "ScoreV2",
        "Mirror",
    ];
    const IS_ZERO_INDEXED_FLAGS: bool = true;
    const NAME: &'static str = "Mod";
}

impl IntFlag<5> for Key {
    const FLAG_NAMES: [&'static str; Self::NUM_FLAGS] = ["M1", "M2", "K1", "K2", "SMOKE"];

    fn new(value: i32) -> Key {
        Key(value.try_into().unwrap())
    }

    type FlagType = Key;

    fn value(&self) -> i32 {
        self.0.try_into().unwrap()
    }

    const IS_ZERO_INDEXED_FLAGS: bool = false;
    const NAME: &'static str = "Key";
}

impl IntFlag<4> for KeyTaiko {
    const FLAG_NAMES: [&'static str; Self::NUM_FLAGS] =
        ["LEFT_DON", "LEFT_KAT", "RIGHT_DON", "RIGHT_KAT"];

    fn new(value: i32) -> KeyTaiko {
        KeyTaiko(value)
    }

    type FlagType = KeyTaiko;

    fn value(&self) -> i32 {
        self.0
    }

    const IS_ZERO_INDEXED_FLAGS: bool = false;
    const NAME: &'static str = "KeyTaiko";
}

impl IntFlag<18> for KeyMania {
    const FLAG_NAMES: [&'static str; Self::NUM_FLAGS] = [
        "K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9", "K10", "K11", "K12", "K13", "K14",
        "K15", "K16", "K17", "K18",
    ];

    fn new(value: i32) -> KeyMania {
        KeyMania(value)
    }

    type FlagType = KeyMania;

    fn value(&self) -> i32 {
        self.0
    }

    const IS_ZERO_INDEXED_FLAGS: bool = false;
    const NAME: &'static str = "KeyMania";
}

impl From<i32> for Mod {
    fn from(int: i32) -> Mod {
        Mod(int as u32)
    }
}
