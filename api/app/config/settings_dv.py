"""
Development (dv) settings — overrides to be applied on top of base_settings.

Only specify fields that differ from base_settings.
"""

from .settings import Environment, Settings, ApiSettings


dv_settings = Settings(
    environment=Environment.DEVELOPMENT,
    api=ApiSettings(
        uvicorn_reload=True,
    ),
)
