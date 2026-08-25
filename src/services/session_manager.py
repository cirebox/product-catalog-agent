"""
SessionManager with HTTP persistence + in-memory fallback.

Tries to persist sessions via the backend REST API (PostgreSQL).
Falls back to an in-memory LRU cache when the backend is unavailable,
ensuring multi-turn flows still work within a single process lifetime.

Endpoint contract (vamu-colombo /mcp/sessions):
  GET    /mcp/sessions/{phone}/{channel}           → SessionData | 404
  PUT    /mcp/sessions/{phone}/{channel}           → SessionData
  DELETE /mcp/sessions/{phone}/{channel}           → { deleted: true } | 404
"""

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a single user/channel conversation session."""

    phone: str
    channel: str
    history: List[Dict[str, Any]] = field(default_factory=list)
    pending_intent: Optional[str] = None
    pending_entities: Dict[str, Any] = field(default_factory=dict)

    @property
    def messages(self) -> List[Dict[str, Any]]:
        return self.history

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "pending_intent": self.pending_intent,
            "pending_entities": self.pending_entities,
        }

    @metadata.setter
    def metadata(self, value: Dict[str, Any]) -> None:
        self.pending_intent = value.get("pending_intent")
        self.pending_entities = value.get("pending_entities", {})

    MAX_HISTORY_SIZE: int = 50

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the session history, truncating if needed."""
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.MAX_HISTORY_SIZE:
            self.history = self.history[-self.MAX_HISTORY_SIZE :]

    @property
    def session_id(self) -> str:
        return f"{self.phone}:{self.channel}"


class SessionManager:
    """
    Session manager with HTTP persistence and in-memory fallback.

    When the backend session endpoint is available, sessions are persisted
    server-side (PostgreSQL, TTL=1h). When it's not (404/connection error),
    sessions are kept in a local LRU cache (max 500 entries, TTL=1h).
    """

    _LOCAL_MAX_ENTRIES = 500
    _LOCAL_TTL_SECONDS = 3600  # 1 hour

    def __init__(
        self, base_url: str = "http://localhost:3000", api_key: str = ""
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        }
        self._client = httpx.Client(timeout=5.0)
        # In-memory fallback: key → (Session, created_at)
        self._local: OrderedDict[str, tuple[Session, float]] = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_create(self, phone: str, channel: str = "whatsapp") -> Session:
        """Return existing active session or create a new one.

        When no session exists, attempts to recover recent conversation
        context from WhatsAppMessage history via the backend API.
        """
        existing = self._fetch(phone, channel)
        if existing is not None:
            return existing
        logger.debug("No active session for %s/%s — starting fresh", phone, channel)

        # Try to recover context from WhatsApp message history
        recovered_history = self._fetch_recent_messages(phone)
        if recovered_history:
            logger.info(
                "Recovered %d messages from WhatsAppMessage for %s/%s",
                len(recovered_history),
                phone,
                channel,
            )
        return Session(phone=phone, channel=channel, history=recovered_history)

    def get(self, phone: str, channel: str = "whatsapp") -> Optional[Session]:
        """Return active session or None if not found/expired."""
        return self._fetch(phone, channel)

    def save(self, session: Session) -> None:
        """Persist session (tries HTTP, falls back to local cache)."""
        self._upsert(session)
        # Always keep a local copy for fast access and fallback
        self._local_put(session)

    def delete(self, phone: str, channel: str = "whatsapp") -> bool:
        """Delete session by (phone, channel)."""
        key = f"{phone}:{channel}"
        with self._lock:
            self._local.pop(key, None)
        url = f"{self._base_url}/mcp/sessions/{quote(phone)}/{quote(channel)}"
        try:
            resp = self._client.delete(url, headers=self._headers)
            return resp.status_code in (200, 204)
        except httpx.RequestError:
            return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List locally cached sessions."""
        now = time.monotonic()
        with self._lock:
            return [
                {"session_id": key, "age_s": int(now - ts)}
                for key, (_, ts) in self._local.items()
                if now - ts < self._LOCAL_TTL_SECONDS
            ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch(self, phone: str, channel: str) -> Optional[Session]:
        """Try remote fetch, fall back to local cache."""
        # Try remote first
        session = self._fetch_remote(phone, channel)
        if session is not None:
            self._local_put(session)
            return session
        # Fall back to local cache
        return self._local_get(phone, channel)

    def _fetch_remote(self, phone: str, channel: str) -> Optional[Session]:
        url = f"{self._base_url}/mcp/sessions/{quote(phone)}/{quote(channel)}"
        try:
            resp = self._client.get(url, headers=self._headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            return Session(
                phone=data["phone"],
                channel=data["channel"],
                history=data.get("history", []),
                pending_intent=data.get("pendingIntent"),
                pending_entities=data.get("pendingEntities") or {},
            )
        except httpx.RequestError:
            return None
        except Exception as exc:
            logger.debug("Session fetch error %s/%s: %s", phone, channel, exc)
            return None

    def _fetch_recent_messages(
        self, phone: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Recover recent conversation history from WhatsAppMessage table."""
        url = f"{self._base_url}/mcp/messages/{quote(phone)}/recent"
        try:
            resp = self._client.get(
                url, headers=self._headers, params={"limit": str(limit)}
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            messages = data.get("messages", [])
            history: List[Dict[str, Any]] = []
            for msg in messages:
                content = msg.get("content")
                if not content:
                    continue
                direction = msg.get("direction", "")
                role = "user" if direction == "incoming" else "assistant"
                history.append({"role": role, "content": content})
            return history
        except Exception as exc:
            logger.debug("Fetch recent messages failed for %s: %s", phone, exc)
            return []

    def _upsert(self, session: Session) -> None:
        url = f"{self._base_url}/mcp/sessions/{quote(session.phone)}/{quote(session.channel)}"
        payload = {
            "history": session.history[-20:],
            "pendingIntent": session.pending_intent,
            "pendingEntities": session.pending_entities or {},
        }
        try:
            resp = self._client.put(url, json=payload, headers=self._headers)
            if resp.status_code == 404:
                logger.debug(
                    "Session endpoint not available for %s/%s — using local cache only",
                    session.phone,
                    session.channel,
                )
                return
            resp.raise_for_status()
            logger.debug(
                "Session saved remotely for %s/%s", session.phone, session.channel
            )
        except httpx.RequestError as exc:
            logger.debug(
                "Session upsert network error %s/%s: %s",
                session.phone,
                session.channel,
                exc,
            )
        except Exception as exc:
            logger.debug(
                "Session upsert error %s/%s: %s", session.phone, session.channel, exc
            )

    # ------------------------------------------------------------------
    # Local LRU cache
    # ------------------------------------------------------------------

    def _local_put(self, session: Session) -> None:
        key = session.session_id
        with self._lock:
            self._local[key] = (session, time.monotonic())
            self._local.move_to_end(key)
            # Evict oldest entries if over capacity
            while len(self._local) > self._LOCAL_MAX_ENTRIES:
                self._local.popitem(last=False)

    def _local_get(self, phone: str, channel: str) -> Optional[Session]:
        key = f"{phone}:{channel}"
        with self._lock:
            entry = self._local.get(key)
            if entry is None:
                return None
            session, created_at = entry
            if time.monotonic() - created_at > self._LOCAL_TTL_SECONDS:
                self._local.pop(key, None)
                return None
            self._local.move_to_end(key)
            return session
