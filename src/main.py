"""ASGI main application entrypoint."""

from src.infrastructure.fastapi.server import create_app

app = create_app()

__all__ = ["app", "create_app"]
