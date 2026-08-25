"""
Tests for SQLiteService.
"""

import asyncio
import tempfile

import pytest
from src.services.sqlite_service import SQLiteService


@pytest.fixture
def sqlite_service():
    """Create a SQLiteService for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = f"{tmp_dir}/test.db"
        service = SQLiteService(db_path=db_path)
        asyncio.run(service.initialize())
        yield service


class TestSQLiteService:
    """Tests for SQLite service."""

    def test_initialize(self, sqlite_service):
        """Test that database initializes correctly."""
        stats = asyncio.run(sqlite_service.get_stats())
        assert stats["sessions"] == 0
        assert stats["messages"] == 0

    def test_create_session(self, sqlite_service):
        """Test creating a session."""
        result = asyncio.run(sqlite_service.create_session("test-123"))
        assert result["session_id"] == "test-123"

    def test_get_session(self, sqlite_service):
        """Test getting a session."""
        asyncio.run(sqlite_service.create_session("test-456"))
        session = asyncio.run(sqlite_service.get_session("test-456"))
        assert session is not None
        assert session["session_id"] == "test-456"

    def test_add_message(self, sqlite_service):
        """Test adding a message."""
        asyncio.run(sqlite_service.create_session("test-789"))
        result = asyncio.run(
            sqlite_service.add_message(
                session_id="test-789",
                role="user",
                content="Olá",
                intent="greeting",
            )
        )
        assert result["status"] == "added"

    def test_get_messages(self, sqlite_service):
        """Test getting messages for a session."""
        asyncio.run(sqlite_service.create_session("test-msg"))
        asyncio.run(
            sqlite_service.add_message("test-msg", "user", "Olá", "greeting")
        )
        asyncio.run(
            sqlite_service.add_message("test-msg", "assistant", "Olá! Como posso ajudar?")
        )

        messages = asyncio.run(sqlite_service.get_messages("test-msg"))
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_delete_session(self, sqlite_service):
        """Test deleting a session."""
        asyncio.run(sqlite_service.create_session("test-del"))
        asyncio.run(
            sqlite_service.add_message("test-del", "user", "Teste")
        )

        result = asyncio.run(sqlite_service.delete_session("test-del"))
        assert result is True

        session = asyncio.run(sqlite_service.get_session("test-del"))
        assert session is None

    def test_list_sessions(self, sqlite_service):
        """Test listing sessions."""
        asyncio.run(sqlite_service.create_session("s1"))
        asyncio.run(sqlite_service.create_session("s2"))
        asyncio.run(sqlite_service.create_session("s3"))

        sessions = asyncio.run(sqlite_service.list_sessions())
        assert len(sessions) == 3

    def test_get_stats(self, sqlite_service):
        """Test getting database statistics."""
        asyncio.run(sqlite_service.create_session("s1"))
        asyncio.run(sqlite_service.add_message("s1", "user", "Test"))

        stats = asyncio.run(sqlite_service.get_stats())
        assert stats["sessions"] == 1
        assert stats["messages"] == 1
