"""Poetry script entrypoint for Fly Search API."""

import uvicorn

from fly_search.config import get_settings


def main() -> None:
    """Run dev server."""
    settings = get_settings()
    uvicorn.run(
        "fly_search.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        factory=False,
    )


if __name__ == "__main__":
    main()
