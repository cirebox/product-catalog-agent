"""
Shared test fixtures for Product Catalog Agent tests.
"""

import tempfile

import pytest


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    import os
    if os.path.exists(db_path):
        os.unlink(db_path)
