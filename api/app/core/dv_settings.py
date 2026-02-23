"""
Development (dv) settings — overrides applied on top of base.

Only specify fields that differ from base_settings.
"""

from app.core.settings import Settings, ApiSettings

dv_settings = Settings(
    environment="development",
    api=ApiSettings(
        debug=True,
    ),
)
