"""
Config type primitives used by the settings dataclasses.

Provides the ``EMPTY`` sentinel, the ``OptionalSetting`` type wrapper,
and the ``@settings_dataclass`` decorator.
"""

from dataclasses import dataclass, field
from typing import Union, get_args, get_origin


class _EmptySetting:
    """
    Sentinel indicating a setting has not been specified.

    Use the module-level ``EMPTY`` instance rather than constructing
    new instances.
    """

    def __repr__(self) -> str:
        return "EMPTY"

    def __bool__(self) -> bool:
        return False


EMPTY = _EmptySetting()
"""Module-level singleton used as the default for all settings fields."""


class SettingsValue:
    """
    Type wrapper: ``SettingsValue[T]`` resolves to ``Union[T, _EmptySetting]``.

    Used in combination with ``@settings_dataclass`` which auto-defaults
    any ``SettingsValue`` field to ``EMPTY``.
    """

    def __class_getitem__(cls, item):
        return Union[item, _EmptySetting]


def _empty() -> _EmptySetting:
    """``default_factory`` that returns the ``EMPTY`` sentinel."""
    return EMPTY


def settings_dataclass(cls):
    """
    Class decorator that auto-defaults ``SettingsValue`` fields to
    ``EMPTY``, then applies ``@dataclass(frozen=True)``.
    """
    for name, annotation in cls.__annotations__.items():
        if get_origin(annotation) is Union and _EmptySetting in get_args(annotation):
            if name not in cls.__dict__:
                setattr(cls, name, field(default_factory=_empty))
    return dataclass(frozen=True)(cls)
