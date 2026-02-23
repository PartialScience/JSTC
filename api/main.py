from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import application modules
from app.config import Config, base_settings, local_settings
from app.routers import items, health

# Settings
settings = Config(base=base_settings, env=local_settings)

# Create FastAPI instance
app = FastAPI(
    title=settings.api.title,
    description=settings.api.description,
    version=settings.api.version,
    docs_url=settings.api.docs_url,
    redoc_url=settings.api.redoc_url,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
)

# Include routers
app.include_router(health.router)
app.include_router(items.router)

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
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.uvicorn_reload,
    )
