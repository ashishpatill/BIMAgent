import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL", "86400"))  # 24h default


class Session(BaseModel):
    session_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    skill_results: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionStore(ABC):
    @abstractmethod
    async def create_session(self, session: Session | None = None) -> Session: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Session | None: ...

    @abstractmethod
    async def update_session(self, session: Session) -> Session: ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool: ...

    @abstractmethod
    async def list_sessions(self, limit: int = 100) -> list[Session]: ...


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def create_session(self, session: Session | None = None) -> Session:
        if session is None:
            session = Session(session_id=str(uuid.uuid4()))
        self._sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def update_session(self, session: Session) -> Session:
        session.updated_at = datetime.now(timezone.utc)
        self._sessions[session.session_id] = session
        return session

    async def delete_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    async def list_sessions(self, limit: int = 100) -> list[Session]:
        return list(self._sessions.values())[:limit]


class RedisSessionStore(SessionStore):
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "bimagent:session:",
        ttl: int = SESSION_TTL_SECONDS,
    ):
        self._redis_url = redis_url
        self._prefix = prefix
        self._ttl = ttl
        self._redis: Any = None

    async def _get_redis(self) -> Any:
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
        return self._redis

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"

    async def create_session(self, session: Session | None = None) -> Session:
        try:
            r = await self._get_redis()
            if session is None:
                session = Session(session_id=str(uuid.uuid4()))
            await r.set(self._key(session.session_id), session.model_dump_json(), ex=self._ttl)
            return session
        except Exception as e:
            logger.error("Redis create_session failed: %s", e)
            raise

    async def get_session(self, session_id: str) -> Session | None:
        try:
            r = await self._get_redis()
            data = await r.get(self._key(session_id))
            if data is None:
                return None
            session = Session.model_validate_json(data)
            # Refresh TTL on access
            await r.expire(self._key(session_id), self._ttl)
            return session
        except Exception as e:
            logger.warning("Redis get_session failed: %s", e)
            return None

    async def update_session(self, session: Session) -> Session:
        try:
            session.updated_at = datetime.now(timezone.utc)
            r = await self._get_redis()
            await r.set(self._key(session.session_id), session.model_dump_json(), ex=self._ttl)
            return session
        except Exception as e:
            logger.error("Redis update_session failed: %s", e)
            raise

    async def delete_session(self, session_id: str) -> bool:
        try:
            r = await self._get_redis()
            return await r.delete(self._key(session_id)) > 0
        except Exception as e:
            logger.error("Redis delete_session failed: %s", e)
            return False

    async def list_sessions(self, limit: int = 100) -> list[Session]:
        try:
            r = await self._get_redis()
            cursor = 0
            keys: list[str] = []
            while len(keys) < limit:
                cursor, batch = await r.scan(cursor=cursor, match=f"{self._prefix}*", count=limit)
                keys.extend(batch)
                if cursor == 0:
                    break
            sessions: list[Session] = []
            for key in sorted(keys)[:limit]:
                data = await r.get(key)
                if data:
                    sessions.append(Session.model_validate_json(data))
            return sessions
        except Exception as e:
            logger.error("Redis list_sessions failed: %s", e)
            return []


_store_instance: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            store = RedisSessionStore(redis_url=redis_url)
            _store_instance = store
            logger.info("Using RedisSessionStore (url=%s)", redis_url)
            return _store_instance
        except Exception as e:
            logger.warning(
                "Failed to initialize RedisSessionStore: %s. Falling back to InMemorySessionStore.",
                e,
            )

    _store_instance = InMemorySessionStore()
    logger.info("Using InMemorySessionStore (Redis unavailable)")
    return _store_instance
