"""Shared pytest fixtures and configuration for all backend tests."""
import pytest

from app.main import app as flask_app


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable Flask-Limiter for all tests so rate-limit counters don't bleed between tests."""
    flask_app.config["RATELIMIT_ENABLED"] = False
    yield
    flask_app.config["RATELIMIT_ENABLED"] = True
