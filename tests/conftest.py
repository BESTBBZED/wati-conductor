"""Pytest configuration for wati-conductor tests."""

import pytest


@pytest.fixture(autouse=True)
def _reset_db_engine():
    """Reset the DB engine before each test to avoid event loop binding issues."""
    from conductor.db.session import reset_engine
    reset_engine()
    yield
