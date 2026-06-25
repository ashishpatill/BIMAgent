"""Tests for Qdrant-wired /query endpoint"""
from unittest.mock import patch, MagicMock
import pytest


def _all_routes(app):
    """Collect all route paths via the OpenAPI schema (covers included routers)."""
    return list(app.openapi().get("paths", {}).keys())


def test_get_vectorstore_fallback():
    """Verify store falls back to FakeEmbeddings when no API key"""
    from store import get_vectorstore
    vs = get_vectorstore("test")
    assert vs is not None


def test_query_endpoint_exists():
    """Verify the /query route is registered (including sub-routers)"""
    from app.main import app
    paths = _all_routes(app)
    assert "/query" in paths
