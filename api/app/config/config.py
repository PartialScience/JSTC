"""
Configuration for JSTC API.

Merges environment-specific settings on top of base settings
to produce a single resolved Config instance.
"""

import copy
from dataclasses import fields as dc_fields

from .settings import Settings
from .types import _EmptySetting


class Config(Settings):
    """
    Resolved application configuration.

    Inherits ``Settings`` so every field is available directly.
    Accepts a *base* ``Settings`` and an environment-specific ``Settings``,
    then merges the environment values on top of the base at construction
    time.
    """

    def __init__(self, base: Settings, env: Settings) -> None:
        merged: Settings = self._merge_dataclass(base, env)
        for f in dc_fields(merged):
            object.__setattr__(self, f.name, getattr(merged, f.name))

    def _merge_dataclass(self, base, override):
        """
        Recursively merge *override* on top of *base*.

        For every field in *override* that is not ``EMPTY``, the value
        replaces the corresponding field in *base*.  Nested dataclass
        fields are merged recursively so partial overrides work at any
        depth.

        Returns a deep-copied result; neither input is mutated.
        """
        if isinstance(override, _EmptySetting):
            return copy.deepcopy(base)
        if isinstance(base, _EmptySetting):
            return copy.deepcopy(override)

        merged_kwargs = {}
        for f in dc_fields(base):
            base_val = getattr(base, f.name)
            override_val = getattr(override, f.name)
            if not isinstance(override_val, _EmptySetting):
                if hasattr(override_val, "__dataclass_fields__"):
                    merged_kwargs[f.name] = self._merge_dataclass(base_val, override_val)
                else:
                    merged_kwargs[f.name] = copy.deepcopy(override_val)
            else:
                merged_kwargs[f.name] = copy.deepcopy(base_val)
        return type(base)(**merged_kwargs)