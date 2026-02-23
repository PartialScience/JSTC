"""
Settings dataclass definitions for JSTC API.

All fields are Optional so that environment-specific files
only need to specify the values they want to override.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ApiSettings:
    title: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    debug: Optional[bool] = None
    docs_url: Optional[str] = None
    redoc_url: Optional[str] = None


@dataclass
class DatabaseSettings:
    url: Optional[str] = None


@dataclass
class CorsSettings:
    allow_origins: Optional[List[str]] = None
    allow_credentials: Optional[bool] = None
    allow_methods: Optional[List[str]] = None
    allow_headers: Optional[List[str]] = None


@dataclass
class PaginationSettings:
    default_page_size: Optional[int] = None
    max_page_size: Optional[int] = None


@dataclass
class Settings:
    environment: Optional[str] = None
    api: Optional[ApiSettings] = None
    database: Optional[DatabaseSettings] = None
    cors: Optional[CorsSettings] = None
    pagination: Optional[PaginationSettings] = None
