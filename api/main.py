import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import application modules
from app.config import Config, base_settings, local_settings
from app.routers import health, simulation
from app.warmup import run_warmup

logger = logging.getLogger("jstc")

# Settings
settings = Config(base=base_settings, env=local_settings)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown. Optionally warm the FEM stack (Numba JIT, MKL, gmsh)
    before serving so the first real request isn't slow. Enabled in
    production via JSTC_WARMUP=1; off by default so tests/dev boot fast."""
    if _env_flag("JSTC_WARMUP"):
        logger.info("Warming up FEM stack...")
        took = run_warmup()
        logger.info("Warmup %s (%.1fs)", "complete" if took >= 0 else "FAILED", took)
    yield


# Create FastAPI instance
app = FastAPI(
    title=settings.api.title,
    description=settings.api.description,
    version=settings.api.version,
    docs_url=settings.api.docs_url,
    redoc_url=settings.api.redoc_url,
    lifespan=lifespan,
)

# CORS. Defaults come from settings (["*"] for local dev). In production set
# JSTC_CORS_ORIGINS (comma-separated exact origins, e.g. the Vercel URL) and
# optionally JSTC_CORS_ORIGIN_REGEX (e.g. https://.*\.vercel\.app to allow
# preview deployments). A regex or explicit origins should replace "*" once
# the frontend's real origin is known.
_cors_origins = settings.cors.allow_origins
_origins_env = os.environ.get("JSTC_CORS_ORIGINS")
if _origins_env:
    _cors_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
_cors_kwargs = dict(
    allow_origins=_cors_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
)
_origin_regex = os.environ.get("JSTC_CORS_ORIGIN_REGEX")
if _origin_regex:
    _cors_kwargs["allow_origin_regex"] = _origin_regex

app.add_middleware(CORSMiddleware, **_cors_kwargs)

# Include routers
app.include_router(health.router)
app.include_router(simulation.router)

# Root endpoint
@app.get("/", tags=["root"])
async def read_root():
    """
    Root endpoint providing basic API information.
    """
    return {
        "message": f"Welcome to {settings.api.title}",
        "version": settings.api.version,
        "environment": settings.environment,
        "docs_url": settings.api.docs_url,
        "health_check": "/health"
    }

if __name__ == "__main__":
    import os

    # Reload defaults to the settings value, but JSTC_UVICORN_RELOAD overrides
    # it. The combined `npm run dev` stack sets it to false: this backend
    # imports numba/mfem/gmsh (~10s), and a reloader restart makes the API
    # briefly unreachable during that re-import, which surfaces to the
    # frontend as a proxy ECONNREFUSED. Run `python main.py` directly (no
    # override) to keep hot-reload for backend development.
    reload = settings.api.uvicorn_reload
    override = os.environ.get("JSTC_UVICORN_RELOAD")
    if override is not None:
        reload = override.strip().lower() in ("1", "true", "yes", "on")

    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=reload,
    )
