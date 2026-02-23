"""
Local (local) settings — overrides to be applied on top of base_settings.

Only specify fields that differ from base_settings.
"""

from .settings import Environment, Settings, ApiSettings


local_settings = Settings(
    environment=Environment.LOCAL,
    api=ApiSettings(
        uvicorn_reload=True,
    ),
)
