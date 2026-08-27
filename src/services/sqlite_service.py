"""
SQLite Service — Product Catalog Agent
Gerencia persistência de sessões e histórico de conversas.
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

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

            # Products table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ref TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    price REAL NOT NULL,
                    cost_price REAL DEFAULT 0,
                    margin REAL DEFAULT 0,
                    stock INTEGER NOT NULL DEFAULT 0,
                    manufacturer TEXT DEFAULT '',
                    material TEXT DEFAULT '',
                    size TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP NULL
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_ref ON products(ref)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)
            """)

            # Categories table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Customers table (CRM)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT UNIQUE,
                    email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)
            """)

            # Sales table (replaces orders + payments)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT REFERENCES customers(id),
                    session_id TEXT,
                    total REAL NOT NULL,
                    discount REAL DEFAULT 0,
                    payment_method TEXT NOT NULL,
                    payment_days INTEGER,
                    sale_date TEXT NOT NULL,
                    due_date TEXT,
                    payment_status TEXT DEFAULT 'pendente',
                    paid_date TEXT,
                    paid_amount REAL,
                    payment_note TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales(customer_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sales_status ON sales(payment_status)
            """)

            # Sale items table (normalized)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sale_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id TEXT REFERENCES sales(id),
                    product_id TEXT,
                    product_name TEXT,
                    variant_color TEXT,
                    variant_size TEXT,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    cost_price REAL DEFAULT 0,
                    subtotal REAL NOT NULL
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id)
            """)

            # Customer notes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS customer_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT REFERENCES customers(id),
                    note_type TEXT DEFAULT 'observacao',
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'aberto',
                    pinned INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_customer ON customer_notes(customer_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_status ON customer_notes(status)
            """)

            # Feedback table (RLHF)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT DEFAULT '',
                    intent TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(id),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_intent ON feedback(intent)
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
        """Add a message to a session. Returns the message ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO messages (session_id, role, content, intent, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, role, content, intent, json.dumps(metadata or {}))
            )
            message_id = cursor.lastrowid

            # Update session timestamp
            await db.execute(
                """UPDATE sessions SET updated_at = CURRENT_TIMESTAMP
                   WHERE session_id = ?""",
                (session_id,)
            )

            await db.commit()

        return {"status": "added", "session_id": session_id, "message_id": message_id}

    async def update_session_metadata(self, session_id: str) -> dict:
        """Build and persist strategic metadata for a session based on its messages and feedback."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get all messages for this session
            async with db.execute(
                """SELECT id, role, content, intent, metadata, created_at
                   FROM messages WHERE session_id = ?
                   ORDER BY created_at ASC""",
                (session_id,)
            ) as cursor:
                messages = [dict(row) for row in await cursor.fetchall()]

            if not messages:
                return {"status": "no_messages"}

            # Get feedback for this session
            async with db.execute(
                """SELECT f.message_id, f.rating, f.comment, f.intent
                   FROM feedback f
                   WHERE f.session_id = ?""",
                (session_id,)
            ) as cursor:
                feedbacks = [dict(row) for row in await cursor.fetchall()]

            # Build metadata
            metadata = self._build_session_metadata(messages, feedbacks)

            # Persist metadata
            await db.execute(
                """UPDATE sessions SET metadata = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE session_id = ?""",
                (json.dumps(metadata, ensure_ascii=False), session_id)
            )
            await db.commit()

        return {"status": "updated", "metadata": metadata}

    def _build_session_metadata(self, messages: List[Dict], feedbacks: List[Dict]) -> Dict[str, Any]:
        """Build strategic metadata from messages and feedbacks."""
        user_msgs = [m for m in messages if m["role"] == "user"]
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]

        # Intent distribution
        intent_counts = {}
        for msg in assistant_msgs:
            intent = msg.get("intent", "") or "unknown"
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        # Last intent
        last_intent = ""
        for msg in reversed(assistant_msgs):
            if msg.get("intent"):
                last_intent = msg["intent"]
                break

        # Products mentioned (extract from user messages)
        products_mentioned = set()
        for msg in user_msgs:
            content = msg.get("content", "").upper()
            # Look for product refs like CAL-001, CUE-002
            import re
            refs = re.findall(r'[A-Z]{2,4}-\d{3}', content)
            products_mentioned.update(refs)

        # Feedback summary
        positive_feedback = sum(1 for f in feedbacks if f.get("rating") == 1)
        negative_feedback = sum(1 for f in feedbacks if f.get("rating") == -1)
        feedback_comments = [f.get("comment", "") for f in feedbacks if f.get("comment")]

        # Session duration
        if len(messages) >= 2:
            first_msg = messages[0]
            last_msg = messages[-1]
            try:
                first_time = datetime.fromisoformat(first_msg["created_at"])
                last_time = datetime.fromisoformat(last_msg["created_at"])
                duration_seconds = int((last_time - first_time).total_seconds())
            except (ValueError, TypeError):
                duration_seconds = 0
        else:
            duration_seconds = 0

        # Average message length
        user_msg_lengths = [len(m.get("content", "")) for m in user_msgs]
        avg_user_msg_length = int(sum(user_msg_lengths) / len(user_msg_lengths)) if user_msg_lengths else 0

        # Engagement score (simple heuristic)
        engagement_score = 0
        if len(user_msgs) > 3:
            engagement_score += 1
        if len(products_mentioned) > 0:
            engagement_score += 1
        if positive_feedback > 0:
            engagement_score += 1
        if duration_seconds > 120:
            engagement_score += 1

        return {
            "summary": {
                "total_messages": len(messages),
                "user_messages": len(user_msgs),
                "assistant_messages": len(assistant_msgs),
                "session_duration_seconds": duration_seconds,
            },
            "intents": {
                "distribution": intent_counts,
                "last_intent": last_intent,
                "unique_intents_count": len(intent_counts),
            },
            "products_discussed": list(products_mentioned),
            "feedback": {
                "positive": positive_feedback,
                "negative": negative_feedback,
                "total": positive_feedback + negative_feedback,
                "comment_count": len(feedback_comments),
                "comments": feedback_comments[:5],
            },
            "engagement": {
                "avg_user_message_length": avg_user_msg_length,
                "products_viewed": len(products_mentioned),
                "score": engagement_score,
            },
            "last_updated": datetime.now().isoformat(),
        }

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

            async with db.execute("SELECT COUNT(*) FROM feedback") as cursor:
                feedback_count = (await cursor.fetchone())[0]

        return {
            "db_path": self.db_path,
            "sessions": session_count,
            "messages": message_count,
            "feedback": feedback_count,
        }

    # ------------------------------------------------------------------
    # Feedback (RLHF)
    # ------------------------------------------------------------------

    async def add_feedback(
        self,
        message_id: int,
        session_id: str,
        rating: int,
        comment: str = "",
        intent: str = "",
    ) -> dict:
        """Add feedback for a message. Rating: 1 (positive) or -1 (negative)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO feedback (message_id, session_id, rating, comment, intent)
                   VALUES (?, ?, ?, ?, ?)""",
                (message_id, session_id, rating, comment, intent),
            )
            await db.commit()
        return {"status": "added", "message_id": message_id, "rating": rating}

    async def has_feedback(self, message_id: int) -> bool:
        """Check if a message already has feedback."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM feedback WHERE message_id = ?", (message_id,)
            ) as cursor:
                count = (await cursor.fetchone())[0]
                return count > 0

    async def get_feedback_stats(self) -> dict:
        """Get aggregate feedback stats. Implicit positives = messages without feedback."""
        async with aiosqlite.connect(self.db_path) as db:
            # Total assistant messages
            async with db.execute(
                "SELECT COUNT(*) FROM messages WHERE role = 'assistant'"
            ) as cursor:
                total_messages = (await cursor.fetchone())[0]

            # Explicit positive
            async with db.execute(
                "SELECT COUNT(*) FROM feedback WHERE rating = 1"
            ) as cursor:
                positive = (await cursor.fetchone())[0]

            # Explicit negative
            async with db.execute(
                "SELECT COUNT(*) FROM feedback WHERE rating = -1"
            ) as cursor:
                negative = (await cursor.fetchone())[0]

            # No feedback (implicit positive)
            implicit = total_messages - positive - negative

            # Approval rate = (explicit positive + implicit) / total
            approval_rate = (
                ((positive + implicit) / total_messages * 100)
                if total_messages > 0
                else 0
            )

        return {
            "total_messages": total_messages,
            "positive": positive,
            "negative": negative,
            "implicit_positive": implicit,
            "approval_rate": round(approval_rate, 1),
        }

    async def get_feedback_by_intent(self) -> list:
        """Get feedback stats grouped by intent."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT
                    m.intent,
                    COUNT(CASE WHEN f.rating = 1 THEN 1 END) as positive,
                    COUNT(CASE WHEN f.rating = -1 THEN 1 END) as negative,
                    COUNT(CASE WHEN f.rating IS NULL THEN 1 END) as no_feedback,
                    COUNT(*) as total
                FROM messages m
                LEFT JOIN feedback f ON m.id = f.message_id
                WHERE m.role = 'assistant' AND m.intent != ''
                GROUP BY m.intent
                ORDER BY total DESC
                """
            ) as cursor:
                rows = await cursor.fetchall()
                result = []
                for row in rows:
                    r = dict(row)
                    # Approval rate including implicit
                    rated_pos = r["positive"] + r["no_feedback"]
                    r["approval_rate"] = (
                        round(rated_pos / r["total"] * 100, 1) if r["total"] > 0 else 0
                    )
                    result.append(r)
                return result

    async def get_negative_feedback_with_context(self, limit: int = 50) -> list:
        """Get negative feedback with the original question and response."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT
                    f.id as feedback_id,
                    f.rating,
                    f.comment,
                    f.intent,
                    f.created_at as feedback_at,
                    q.content as question,
                    a.content as answer
                FROM feedback f
                JOIN messages a ON f.message_id = a.id
                JOIN messages q ON a.session_id = q.session_id
                    AND q.role = 'user'
                    AND q.created_at < a.created_at
                WHERE f.rating = -1
                ORDER BY f.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_good_examples(self, intent: str, limit: int = 3) -> list:
        """Get good responses (👍 or implicit) for few-shot examples."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT
                    q.content as question,
                    a.content as answer
                FROM messages a
                JOIN messages q ON a.session_id = q.session_id
                    AND q.role = 'user'
                    AND q.created_at < a.created_at
                LEFT JOIN feedback f ON a.id = f.message_id
                WHERE a.role = 'assistant'
                    AND a.intent = ?
                    AND (f.rating = 1 OR f.rating IS NULL)
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (intent, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def export_feedback(self) -> list:
        """Export all feedback with context for fine-tuning."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT
                    q.content as question,
                    a.content as response,
                    a.intent,
                    f.rating,
                    f.comment,
                    f.created_at
                FROM feedback f
                JOIN messages a ON f.message_id = a.id
                JOIN messages q ON a.session_id = q.session_id
                    AND q.role = 'user'
                    AND q.created_at < a.created_at
                ORDER BY f.created_at DESC
                """
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
