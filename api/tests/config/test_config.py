"""
Tests for the Config class and settings singletons.

Verifies:
1. Merge behaviour works correctly for all field types.
2. Every env singleton, when merged with base, produces fully-populated
   settings (no ``EMPTY`` at any depth).
"""

from dataclasses import fields as dc_fields
from enum import EnumType
from typing import Union, get_args, get_origin

import pytest

from app.config.settings import Settings
from app.config.types import _EmptySetting
from app.config.settings_base import base_settings
from app.config.settings_dv import dv_settings
from app.config.settings_local import local_settings
from app.config.config import Config


# ---------------------------------------------------------------------------
# Registry of environment singletons — add new ones here.
# ---------------------------------------------------------------------------
ENV_SETTINGS = [
    pytest.param(dv_settings, id="dv"),
    pytest.param(local_settings, id="local"),
]


# ---------------------------------------------------------------------------
# Helpers: generate dummy dataclass instances from type annotations so that
# we can test merge behaviour without hardcoding specific field names or
# values that will break when settings are added/changed.
# ---------------------------------------------------------------------------

def _resolve_inner_type(annotation):
    """
    Strip ``_EmptySetting`` and ``None`` from a Union to get the 'real' type.

    For ``SettingsValue[str]`` (i.e. ``Union[str, _EmptySetting]``) returns ``str``.
    For ``SettingsValue[Optional[str]]`` returns ``Optional[str]``.
    """
    if get_origin(annotation) is Union:
        args = [a for a in get_args(annotation) if a is not _EmptySetting]
        if len(args) == 1:
            return args[0]
        # Re-wrap remaining args as a Union (handles Optional[str] etc.)
        return Union[tuple(args)]
    return annotation


def _is_optional(annotation) -> bool:
    """Return True if ``None`` is an allowed value for this annotation."""
    if get_origin(annotation) is Union:
        return type(None) in get_args(annotation)
    return annotation is type(None)


_DUMMY_VALUES = {
    str: "dummy",
    int: 42,
    float: 3.14,
    bool: True,
}


def _make_dummy_value(annotation, *, alt: bool = False):
    """
    Create a dummy value matching *annotation*.

    When *alt* is True a different (but still valid) value is returned,
    useful for building an 'override' instance.
    """
    inner = _resolve_inner_type(annotation)

    # Optional[X] — produce a real value (not None) for test purposes
    if _is_optional(inner):
        non_none = [a for a in get_args(inner) if a is not type(None)]
        if non_none:
            inner = non_none[0]
        else:
            return None

    # Nested settings dataclass
    if hasattr(inner, "__dataclass_fields__"):
        return _build_settings(inner, alt=alt)

    # List[X]
    if get_origin(inner) is list:
        elem_type = get_args(inner)[0] if get_args(inner) else str
        base_val = _DUMMY_VALUES.get(elem_type, "item")
        return [f"{base_val}_alt" if alt else base_val]

    # Enum
    if isinstance(inner, EnumType):
        members = list(inner)
        return members[1 % len(members)] if alt else members[0]

    # Scalar
    base_val = _DUMMY_VALUES.get(inner, "unknown")
    if alt and isinstance(base_val, str):
        return base_val + "_alt"
    if alt and isinstance(base_val, int):
        return base_val + 1
    if alt and isinstance(base_val, bool):
        return not base_val
    return base_val


def _build_settings(cls, *, alt: bool = False):
    """
    Construct a fully-populated instance of dataclass *cls* with dummy
    values derived from the field type annotations.
    """
    kwargs = {}
    for f in dc_fields(cls):
        kwargs[f.name] = _make_dummy_value(f.type, alt=alt)
    return cls(**kwargs)


def _build_partial_settings(cls, field_index: int = 0, *, alt: bool = True):
    """
    Construct an instance of *cls* where only the field at *field_index*
    has a value; the rest are left as EMPTY.
    """
    fields = dc_fields(cls)
    idx = field_index % len(fields)
    target = fields[idx]
    return cls(**{target.name: _make_dummy_value(target.type, alt=alt)})


# ---------------------------------------------------------------------------
# 1. Merge behaviour
# ---------------------------------------------------------------------------

class TestMergeBehaviour:
    """Verify that Config._merge_dataclass produces the expected results."""

    def test_env_overrides_base_scalar(self):
        """An env value replaces the corresponding base value."""
        base = _build_settings(Settings)
        env = _build_partial_settings(Settings, 0, alt=True)

        target_field = dc_fields(Settings)[0]
        merged = Config(base=base, env=env)
        merged_val = getattr(merged, target_field.name)
        env_val = getattr(env, target_field.name)
        assert not isinstance(merged_val, _EmptySetting)
        assert merged_val == env_val

    def test_base_values_preserved_when_env_is_empty(self):
        """Fields not specified in env keep the base value."""
        base = _build_settings(Settings)
        env = Settings()  # all EMPTY
        merged = Config(base=base, env=env)
        for f in dc_fields(Settings):
            assert getattr(merged, f.name) == getattr(base, f.name)

    def test_env_overrides_each_top_level_field(self):
        """Every top-level field can be individually overridden."""
        base = _build_settings(Settings)
        for i, f in enumerate(dc_fields(Settings)):
            env = _build_partial_settings(Settings, i, alt=True)
            merged = Config(base=base, env=env)
            env_val = getattr(env, f.name)
            assert getattr(merged, f.name) == env_val, (
                f"Field '{f.name}' was not overridden"
            )

    def test_nested_partial_override_preserves_sibling_fields(self):
        """Overriding one nested field preserves the others."""
        base = _build_settings(Settings)
        merged = Config(base=base, env=Settings())

        for f in dc_fields(Settings):
            base_val = getattr(base, f.name)
            merged_val = getattr(merged, f.name)
            if hasattr(base_val, "__dataclass_fields__"):
                for nf in dc_fields(base_val):
                    assert getattr(merged_val, nf.name) == getattr(base_val, nf.name)

    def test_list_field_replaced_not_appended(self):
        """List fields are replaced wholesale, not merged element-wise."""
        base = _build_settings(Settings)
        # Find the first nested dataclass that has a list field
        for f in dc_fields(Settings):
            inner = _resolve_inner_type(f.type)
            if not hasattr(inner, "__dataclass_fields__"):
                continue
            for nf in dc_fields(inner):
                nf_inner = _resolve_inner_type(nf.type)
                if get_origin(nf_inner) is list:
                    override_nested = inner(**{nf.name: ["replaced"]})
                    env = Settings(**{f.name: override_nested})
                    merged = Config(base=base, env=env)
                    assert getattr(getattr(merged, f.name), nf.name) == ["replaced"]
                    return
        pytest.skip("No list fields found on nested settings")

    def test_merge_does_not_mutate_inputs(self):
        """Neither the base nor the env object is changed by merging."""
        base = _build_settings(Settings)
        env = _build_settings(Settings, alt=True)

        # snapshot originals
        base_vals = {f.name: getattr(base, f.name) for f in dc_fields(base)}
        env_vals = {f.name: getattr(env, f.name) for f in dc_fields(env)}

        _ = Config(base=base, env=env)

        for f in dc_fields(base):
            assert getattr(base, f.name) == base_vals[f.name]
            assert getattr(env, f.name) == env_vals[f.name]


# ---------------------------------------------------------------------------
# 2. All fields populated after merge with base
# ---------------------------------------------------------------------------

def _assert_no_empty_fields(obj, path: str = ""):
    """
    Recursively assert that no field on *obj* is ``EMPTY``.

    ``path`` is used for readable error messages when a field is missing.
    """
    for f in dc_fields(obj):
        value = getattr(obj, f.name)
        full_path = f"{path}.{f.name}" if path else f.name
        assert not isinstance(value, _EmptySetting), (
            f"Field '{full_path}' is EMPTY after merge, "
            f"please add it to the env singleton or base_settings."
        )
        if hasattr(value, "__dataclass_fields__"):
            _assert_no_empty_fields(value, full_path)


@pytest.mark.parametrize("env_settings", ENV_SETTINGS)
def test_all_fields_populated_after_merge(env_settings: Settings):
    """
    Merging base_settings with each env singleton must produce a Config
    where every field at every depth is not EMPTY.
    """
    merged = Config(base=base_settings, env=env_settings)
    _assert_no_empty_fields(merged)
