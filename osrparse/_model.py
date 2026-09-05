"""Bind dataclass contracts to native storage in one place."""

from inspect import signature
from typing import TypeVar, cast

from osrparse import _native

T = TypeVar("T")


def restore(cls, state=None):
    instance = cls.__new__(cls)
    if state is not None:
        instance.__dict__.update(state)
    return instance


def _reduce(self, protocol):
    return restore, (type(self),), self.__dict__


def _getattribute(self, name):
    if name == "__dataclass_fields__":
        self._materialize()
    try:
        return object.__getattribute__(self, name)
    except AttributeError:
        return object.__getattribute__(self, "_get_field")(name)


def bind_model(template: type[T], *, methods: tuple[str, ...] = ()) -> type[T]:
    native = getattr(_native, template.__name__)
    for name in (
        "__init__",
        "__repr__",
        "__eq__",
        "__hash__",
        "__annotations__",
        "__dataclass_fields__",
        "__dataclass_params__",
        "__match_args__",
        "__doc__",
    ):
        setattr(native, name, getattr(template, name))
    for name in methods:
        setattr(native, name, template.__dict__[name])
    native.__signature__ = signature(template)
    native.__reduce_ex__ = _reduce
    if hasattr(native, "_materialize"):
        native.__getattribute__ = _getattribute
    if "__dict__" in native.__dict__:
        descriptor = native.__dict__["__dict__"]

        def init_subclass(cls, **kwargs):
            super(native, cls).__init_subclass__(**kwargs)
            previous = cls.__getattribute__

            def getattribute(self, name):
                if name == "__dict__":
                    return descriptor.__get__(self, type(self))
                return previous(self, name)

            cls.__getattribute__ = getattribute

        native.__init_subclass__ = classmethod(init_subclass)
    return cast(type[T], native)
