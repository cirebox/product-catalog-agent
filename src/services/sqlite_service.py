"""
SQLite Service — Product Catalog Agent
Gerencia persistência de sessões e histórico de conversas.
"""

import json
import os
from datetime import datetime
from typing import Optional

import aiosqlite


class SQLiteService:
    def __init__(self, db_path: str = "/data/sqlite/sessions.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    intent TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, created_at)
            """)

            await db.commit()

    async def create_session(self, session_id: str, metadata: dict = None) -> dict:
        """Create a new session."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO sessions (session_id, metadata)
                   VALUES (?, ?)""",
                (session_id, json.dumps(metadata or {}))
            )
            await db.commit()

        return {"session_id": session_id, "created_at": datetime.now().isoformat()}

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: str = "",
        metadata: dict = None
    ) -> dict:
        """Add a message to a session."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO messages (session_id, role, content, intent, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, role, content, intent, json.dumps(metadata or {}))
            )

            # Update session timestamp
            await db.execute(
                """UPDATE sessions SET updated_at = CURRENT_TIMESTAMP
                   WHERE session_id = ?""",
                (session_id,)
            )

            await db.commit()

        return {"status": "added", "session_id": session_id}

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> list:
        """Get recent messages for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM messages
                   WHERE session_id = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (session_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in reversed(rows)]

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM messages WHERE session_id = ?", (session_id,)
            )
            await db.execute(
                "DELETE FROM sessions WHERE session_id = ?", (session_id,)
            )
            await db.commit()
            return True

    async def list_sessions(self, limit: int = 100) -> list:
        """List all sessions."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM sessions
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_stats(self) -> dict:
        """Get database statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM sessions") as cursor:
                session_count = (await cursor.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM messages") as cursor:
                message_count = (await cursor.fetchone())[0]

        return {
            "db_path": self.db_path,
            "sessions": session_count,
            "messages": message_count,
        }
