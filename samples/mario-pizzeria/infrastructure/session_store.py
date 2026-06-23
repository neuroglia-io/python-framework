"""Session store for managing user authentication sessions."""

import json
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, cast

try:
    import redis  # type: ignore[import]

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False


class SessionStore(ABC):
    """Abstract base class for session storage."""

    @abstractmethod
    def create_session(self, tokens: dict, user_info: dict) -> str:
        """Create a new session and return session ID.

        Args:
            tokens: Dict containing access_token, refresh_token, id_token, etc.
            user_info: Dict containing user information from OIDC userinfo endpoint

        Returns:
            Session ID string
        """

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session data by session ID.

        Args:
            session_id: The session identifier

        Returns:
            Dict with 'tokens' and 'user_info' keys, or None if not found/expired
        """

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: The session identifier to delete
        """

    @abstractmethod
    def refresh_session(self, session_id: str, new_tokens: dict) -> None:
        """Update session with new tokens after refresh.

        Args:
            session_id: The session identifier
            new_tokens: Updated token dict
        """


class InMemorySessionStore(SessionStore):
    """Simple in-memory session store for development.

    Warning: Sessions are lost on application restart.
    For production, use RedisSessionStore or similar.
    """

    def __init__(self, session_timeout_hours: int = 1):
        """Initialize the in-memory session store.

        Args:
            session_timeout_hours: How long sessions remain valid (default: 1 hour)
        """
        self._sessions: dict[str, dict] = {}
        self._session_timeout = timedelta(hours=session_timeout_hours)

    def create_session(self, tokens: dict, user_info: dict) -> str:
        """Create a new session and return session ID."""
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()

        self._sessions[session_id] = {
            "tokens": tokens,
            "user_info": user_info,
            "created_at": now,
            "expires_at": now + self._session_timeout,
        }

        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session data by session ID."""
        session = self._sessions.get(session_id)

        if not session:
            return None

        # Check if session expired
        if session["expires_at"] < datetime.utcnow():
            # Clean up expired session
            self.delete_session(session_id)
            return None

        return session

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        self._sessions.pop(session_id, None)

    def refresh_session(self, session_id: str, new_tokens: dict) -> None:
        """Update session with new tokens after refresh."""
        session = self._sessions.get(session_id)

        if session:
            existing_tokens = session.get("tokens", {})
            merged_tokens = dict(existing_tokens)
            merged_tokens.update(new_tokens)
            session["tokens"] = merged_tokens
            # Extend expiration time
            session["expires_at"] = datetime.utcnow() + self._session_timeout

    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions (optional maintenance method).

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired = [sid for sid, session in self._sessions.items() if session["expires_at"] < now]

        for sid in expired:
            self.delete_session(sid)

        return len(expired)


class RedisSessionStore(SessionStore):
    """Redis-based session store for production use.

    Provides stateless, distributed session storage suitable for
    horizontal scaling in Kubernetes and other orchestration platforms.
    Sessions are automatically expired by Redis using TTL.
    """

    def __init__(
        self,
        redis_url: str,
        session_timeout_hours: int = 8,
        key_prefix: str = "session:",
    ):
        """Initialize the Redis session store.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
            session_timeout_hours: How long sessions remain valid (default: 8 hours)
            key_prefix: Prefix for all session keys in Redis (default: "session:")

        Raises:
            RuntimeError: If redis package is not installed
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis package is required for RedisSessionStore. " "Install with: pip install redis")

        self._client = redis.from_url(redis_url, decode_responses=True)  # type: ignore[union-attr]
        self._session_timeout_seconds = int(timedelta(hours=session_timeout_hours).total_seconds())
        self._key_prefix = key_prefix

    def _make_key(self, session_id: str) -> str:
        """Create Redis key from session ID."""
        return f"{self._key_prefix}{session_id}"

    def create_session(self, tokens: dict, user_info: dict) -> str:
        """Create a new session and return session ID."""
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()

        session_data = {
            "tokens": tokens,
            "user_info": user_info,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self._session_timeout_seconds)).isoformat(),
        }

        # Store session in Redis with automatic expiration
        key = self._make_key(session_id)
        self._client.setex(key, self._session_timeout_seconds, json.dumps(session_data))

        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session data by session ID."""
        key = self._make_key(session_id)
        data = self._client.get(key)

        if not data:
            return None

        session = json.loads(cast(str, data))

        # Convert ISO format strings back to datetime objects
        session["created_at"] = datetime.fromisoformat(session["created_at"])
        session["expires_at"] = datetime.fromisoformat(session["expires_at"])

        return session

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        key = self._make_key(session_id)
        self._client.delete(key)

    def refresh_session(self, session_id: str, new_tokens: dict) -> None:
        """Update session with new tokens after refresh."""
        # Get existing session
        session = self.get_session(session_id)

        if not session:
            return

        existing_tokens = session.get("tokens", {})
        merged_tokens = dict(existing_tokens)
        merged_tokens.update(new_tokens)
        session["tokens"] = merged_tokens

        # Extend expiration time
        now = datetime.utcnow()
        session["expires_at"] = now + timedelta(seconds=self._session_timeout_seconds)

        # Convert datetime objects to ISO format for JSON serialization
        session_data = {
            "tokens": session["tokens"],
            "user_info": session["user_info"],
            "created_at": session["created_at"].isoformat(),
            "expires_at": session["expires_at"].isoformat(),
        }

        # Store updated session with renewed TTL
        key = self._make_key(session_id)
        self._client.setex(key, self._session_timeout_seconds, json.dumps(session_data))

    def ping(self) -> bool:
        """Check if Redis connection is healthy.

        Returns:
            True if Redis is responding, False otherwise
        """
        try:
            result = self._client.ping()
            return bool(result) if not isinstance(result, bool) else result
        except Exception:
            return False
