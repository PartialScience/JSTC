"""
Base settings — shared defaults for all environments.
"""

from app.core.settings import (
    Settings,
    ApiSettings,
    DatabaseSettings,
    CorsSettings,
    PaginationSettings,
)

base_settings = Settings(
    environment="base",
    api=ApiSettings(
        title="JSTC API",
        description="Johnson Self-Tuning Coil API",
        version="0.1.0",
        host="0.0.0.0",
        port=8000,
        debug=False,
        docs_url="/docs",
        redoc_url="/redoc",
    ),
    database=DatabaseSettings(
        url="sqlite:///./jstc.db",
    ),
    cors=CorsSettings(
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    pagination=PaginationSettings(
        default_page_size=20,
        max_page_size=100,
    ),
)
