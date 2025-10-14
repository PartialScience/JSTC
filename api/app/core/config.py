"""
Configuration settings for JSTC API

This module handles all application configuration using Dynaconf,
"""

from dynaconf import Dynaconf
from functools import lru_cache
from typing import List

# Create dynaconf settings object
settings = Dynaconf(
    # Configuration files to load (in order)
    # Option 1: Single file with environments (current setup)
    # settings_files=["config.yaml", "config.local.yaml"],
    
    # Option 2: Separate files per environment
    settings_files=[
        "config.yaml",              # Base configuration
        "config.development.yaml",  # Development overrides
        "config.staging.yaml",      # Staging overrides  
        "config.production.yaml",   # Production overrides
        "config.local.yaml",        # Local overrides (gitignored)
    ],
    
    # Environment variables prefix
    envvar_prefix="JSTC",
    
    # Enable environment-specific configs
    environments=True,
    
    # Default environment
    env="development",
    
    # Load environment from ENV_FOR_DYNACONF or DYNACONF_ENV
    env_switcher="ENV_FOR_DYNACONF",
    
    # Enable .env file loading
    load_dotenv=True,
    
    # Merge settings instead of replacing
    merge_enabled=True,
    
    # Enable validation
    validate=True,
)

# Validation schema (optional but recommended)
settings.validators.register(
    # API validation
    settings.validator("api.title", must_exist=True),
    settings.validator("api.version", must_exist=True),
    settings.validator("api.host", must_exist=True),
    settings.validator("api.port", must_exist=True, is_type_of=int, gte=1, lte=65535),
    
    # Database validation
    settings.validator("database.url", must_exist=True),
    
    # Pagination validation
    settings.validator("pagination.default_page_size", must_exist=True, is_type_of=int, gte=1),
    settings.validator("pagination.max_page_size", must_exist=True, is_type_of=int, gte=1),
)


@lru_cache()
def get_settings() -> Dynaconf:
    """
    Get cached settings instance.
    
    This function uses lru_cache to ensure settings are loaded only once.
    """
    return settings


# Convenience functions for commonly accessed settings
def get_api_config():
    """Get API configuration section"""
    return settings.api


def get_database_config():
    """Get database configuration section"""
    return settings.database


def get_cors_config():
    """Get CORS configuration section"""
    return settings.cors


def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return settings.get("api.debug", False)


def get_environment() -> str:
    """Get current environment"""
    return settings.current_env
