"""
Tests for the Settings dataclasses.

Verifies:
1. Every field uses OptionalSetting and defaults to EMPTY.
"""

from dataclasses import fields as dc_fields
from typing import Union, get_args, get_origin

import pytest

from app.config.settings import (
    Settings,
    ApiSettings,
    CorsSettings,
)
from app.config.types import _EmptySetting


# ---------------------------------------------------------------------------
# Collect all settings dataclasses (add new ones here).
# ---------------------------------------------------------------------------
SETTINGS_CLASSES = [
    pytest.param(Settings, id="Settings"),
    pytest.param(ApiSettings, id="ApiSettings"),
    pytest.param(CorsSettings, id="CorsSettings"),
]


# ---------------------------------------------------------------------------
# 1. Every field is an OptionalSetting (Union[X, _EmptySetting])
#    with default_factory returning EMPTY
# ---------------------------------------------------------------------------

def _has_empty_variant(annotation) -> bool:
    """Return True if *annotation* is a Union that includes ``_EmptySetting``."""
    if get_origin(annotation) is Union:
        return _EmptySetting in get_args(annotation)
    return False


@pytest.mark.parametrize("cls", SETTINGS_CLASSES)
def test_all_fields_use_optional_setting_with_empty_default(cls):
    """Every field must be OptionalSetting (Union[..., _EmptySetting]) and default to EMPTY."""
    for f in dc_fields(cls):
        assert _has_empty_variant(f.type), (
            f"{cls.__name__}.{f.name} type does not include _EmptySetting (got {f.type})"
        )
        # frozen dataclasses with default_factory: instantiate with no args and check
        instance = cls()
        value = getattr(instance, f.name)
        assert isinstance(value, _EmptySetting), (
            f"{cls.__name__}.{f.name} default is not EMPTY (got {value!r})"
        )
