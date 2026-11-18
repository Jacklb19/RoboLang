"""Expose the existing FastAPI application to Vercel."""

from web.app import app

__all__ = ["app"]
