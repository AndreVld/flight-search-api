"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from fly_search.api import router
from fly_search.logging_config import configure_logging


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    configure_logging()
    app = FastAPI(title="Fly Search API", version="0.1.0")
    app.include_router(router)

    @app.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        """Simple endpoint to verify that the service is alive."""
        return {"status": "ok"}

    return app


app = create_app()
