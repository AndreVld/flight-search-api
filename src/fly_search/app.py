"""FastAPI application factory."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    app = FastAPI(title="Fly Search API", version="0.1.0")

    @app.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        """Simple endpoint to verify that the service is alive."""
        return {"status": "ok"}

    return app


app = create_app()
