"""
Base settings — shared defaults for all environments.
"""

from .settings import (
    Settings,
    ApiSettings,
    CorsSettings,
)

base_settings = Settings(
    api=ApiSettings(
        title="JSTC API",
        description="Backend for JSTC",
        version="0.1.0",
        host="0.0.0.0",
        port=8000,
        uvicorn_reload=False,
        docs_url=None,
        redoc_url=None,
    ),
    cors=CorsSettings(
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
)
