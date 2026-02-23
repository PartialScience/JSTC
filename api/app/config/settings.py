"""
Settings dataclass definitions for JSTC API.

All fields use ``SettingsValue`` so that environment-specific files
only need to specify the values they want to override. Unset fields
hold the ``EMPTY`` sentinel, distinguishing "not specified" from an
intentional ``None``.
"""

from enum import StrEnum
from typing import List, Optional

from .types import SettingsValue, settings_dataclass


class Environment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "dv"
    PRODUCTION = "pd"


@settings_dataclass
class ApiSettings:
    title: SettingsValue[str]
    """Display name of the API shown in generated docs."""

    description: SettingsValue[str]
    """Long-form description shown in the OpenAPI UI."""

    version: SettingsValue[str]
    """Semantic version string of the API, e.g. ``"1.0.0"``."""

    host: SettingsValue[str]
    """Interface address Uvicorn binds to, e.g. ``"0.0.0.0"``."""

    port: SettingsValue[int]
    """TCP port Uvicorn listens on."""

    uvicorn_reload: SettingsValue[bool]
    """Enable Uvicorn hot-reload (development only)."""

    docs_url: SettingsValue[Optional[str]]
    """URL path for the Swagger UI, e.g. ``"/docs"``. Set to ``None`` to disable."""

    redoc_url: SettingsValue[Optional[str]]
    """URL path for the ReDoc UI, e.g. ``"/redoc"``. Set to ``None`` to disable."""


@settings_dataclass
class CorsSettings:
    allow_origins: SettingsValue[List[str]]
    """List of allowed CORS origins, e.g. ``["https://example.com"]``. Use ``["*"]`` to allow all."""

    allow_credentials: SettingsValue[bool]
    """Whether to allow cookies / authorisation headers in cross-origin requests."""

    allow_methods: SettingsValue[List[str]]
    """HTTP methods permitted in cross-origin requests, e.g. ``["GET", "POST"]``."""

    allow_headers: SettingsValue[List[str]]
    """HTTP request headers permitted in cross-origin requests."""


@settings_dataclass
class Settings:
    environment: SettingsValue[Environment]
    """Active deployment environment."""

    api: SettingsValue[ApiSettings]
    """API server configuration."""

    cors: SettingsValue[CorsSettings]
    """Cross-Origin Resource Sharing (CORS) policy."""
