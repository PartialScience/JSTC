"""
Configuration for JSTC API.

Merges environment-specific settings on top of base settings
to produce a single resolved Config instance.
"""

import copy
from dataclasses import fields as dc_fields

from app.core.settings import Settings
from app.core.base_settings import base_settings
from app.core.dv_settings import dv_settings


class Config:
    """
    Resolved application configuration.

    Accepts a *base* ``Settings`` and an environment-specific ``Settings``,
    then merges the environment values on top of the base at construction
    time.  The merged sub-sections are exposed as attributes.
    """

    def __init__(self, base: Settings, env: Settings) -> None:
        merged: Settings = self._merge_dataclass(base, env)
        self.api = merged.api
        self.database = merged.database
        self.cors = merged.cors
        self.pagination = merged.pagination
        self.environment = merged.environment

    def _merge_dataclass(self, base, override):
        """
        Recursively merge *override* on top of *base*.

        For every field in *override* that is not ``None``, the value replaces
        the corresponding field in *base*.  Nested dataclass fields are merged
        recursively so partial overrides work at any depth.

        Returns a deep-copied result; neither input is mutated.
        """
        if override is None:
            return copy.deepcopy(base)
        if base is None:
            return copy.deepcopy(override)

        result = copy.deepcopy(base)
        for f in dc_fields(override):
            override_val = getattr(override, f.name)
            if override_val is not None:
                base_val = getattr(result, f.name)
                if hasattr(override_val, "__dataclass_fields__"):
                    setattr(result, f.name, self._merge_dataclass(base_val, override_val))
                else:
                    setattr(result, f.name, copy.deepcopy(override_val))
        return result


config = Config(base=base_settings, env=dv_settings)
