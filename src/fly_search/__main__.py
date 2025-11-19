"""Poetry script entrypoint for Fly Search API."""

import uvicorn


def main() -> None:
    """Run dev server."""
    uvicorn.run(
        "fly_search.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        factory=False,
    )


if __name__ == "__main__":
    main()
