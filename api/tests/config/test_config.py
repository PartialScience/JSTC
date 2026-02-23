"""
Tests for the Config class and settings singletons.

Verifies:
1. Merge behaviour works correctly for all field types.
2. Every env singleton, when merged with base, produces fully-populated
   settings (no ``None`` at any depth).
"""

from dataclasses import fields as dc_fields

import pytest

from app.config.settings import (
    Settings,
    ApiSettings,
    CorsSettings,
    Environment,
)
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
# 1. Merge behaviour
# ---------------------------------------------------------------------------

class TestMergeBehaviour:
    """Verify that Config._merge_dataclass produces the expected results."""

    def test_env_overrides_base_scalar(self):
        """An env value replaces the corresponding base value."""
        base = Settings(
            api=ApiSettings(uvicorn_reload=False, title="base"),
        )
        env = Settings(
            api=ApiSettings(uvicorn_reload=True),
        )
        merged = Config(base=base, env=env)
        assert merged.api.uvicorn_reload is True

    def test_base_value_preserved_when_env_is_none(self):
        """Fields not specified in env keep the base value."""
        base = Settings(
            api=ApiSettings(title="keep me", port=9000),
        )
        env = Settings(
            api=ApiSettings(port=3000),
        )
        merged = Config(base=base, env=env)
        assert merged.api.title == "keep me"
        assert merged.api.port == 3000

    def test_env_overrides_environment_field(self):
        """The top-level ``environment`` field is overridden correctly."""
        base = Settings()
        env = Settings(environment=Environment.DEVELOPMENT)
        merged = Config(base=base, env=env)
        assert merged.environment == Environment.DEVELOPMENT

    def test_nested_dataclass_partial_override(self):
        """Only specified nested fields are overridden; others survive."""
        base = Settings(
            cors=CorsSettings(
                allow_origins=["https://example.com"],
                allow_credentials=False,
                allow_methods=["GET"],
                allow_headers=["Content-Type"],
            ),
        )
        env = Settings(
            cors=CorsSettings(allow_credentials=True),
        )
        merged = Config(base=base, env=env)
        assert merged.cors.allow_credentials is True
        assert merged.cors.allow_origins == ["https://example.com"]
        assert merged.cors.allow_methods == ["GET"]
        assert merged.cors.allow_headers == ["Content-Type"]

    def test_list_field_replaced_not_appended(self):
        """List fields are replaced wholesale, not merged element-wise."""
        base = Settings(
            cors=CorsSettings(allow_origins=["a", "b"]),
        )
        env = Settings(
            cors=CorsSettings(allow_origins=["c"]),
        )
        merged = Config(base=base, env=env)
        assert merged.cors.allow_origins == ["c"]

    def test_none_env_returns_base_copy(self):
        """When every env field is EMPTY, the result equals the base."""
        base = Settings(
            environment=Environment.DEVELOPMENT,
            api=ApiSettings(title="original"),
            cors=CorsSettings(allow_origins=["*"]),
        )
        env = Settings()  # all EMPTY
        merged = Config(base=base, env=env)
        assert merged.api.title == "original"
        assert merged.cors.allow_origins == ["*"]

    def test_merge_does_not_mutate_inputs(self):
        """Neither the base nor the env object is changed by merging."""
        base = Settings(api=ApiSettings(title="before"))
        env = Settings(api=ApiSettings(title="after"))
        _ = Config(base=base, env=env)
        assert base.api.title == "before"
        assert env.api.title == "after"


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
