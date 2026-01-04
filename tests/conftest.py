"""
Pytest configuration and shared fixtures.

Provides:
- Flask app and test client fixtures
- Temporary directory fixtures for file-based tests
- Mock configuration for testing without real API keys
"""
import os
import pytest

# Set test environment before importing app
os.environ["OPENROUTER_API_KEY"] = "test-api-key-for-testing"


@pytest.fixture
def app():
    """Create Flask application for testing."""
    from chat_rag_explorer import create_app

    app = create_app()
    app.config.update({
        "TESTING": True,
        "OPENROUTER_API_KEY": "test-api-key-for-testing",
    })
    yield app


@pytest.fixture
def client(app):
    """Flask test client for making requests."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Flask application context for testing services."""
    with app.app_context():
        yield app
