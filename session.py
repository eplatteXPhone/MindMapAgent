"""Session model and in-memory store for brainstorming sessions."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionStatus(Enum):
    ACTIVE = "active"
    ENDED = "ended"
    GENERATING = "generating"
    COMPLETE = "complete"


@dataclass
class Idea:
    text: str
    author: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    id: str
    topic: str
    moderator_token: str
    status: SessionStatus = SessionStatus.ACTIVE
    ideas: list[Idea] = field(default_factory=list)
    participants: set[str] = field(default_factory=set)
    mindmap_html: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


# In-memory store
sessions: dict[str, Session] = {}


def _generate_id(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def create_session(topic: str) -> Session:
    session_id = _generate_id()
    while session_id in sessions:
        session_id = _generate_id()
    moderator_token = secrets.token_urlsafe(16)
    session = Session(id=session_id, topic=topic, moderator_token=moderator_token)
    sessions[session_id] = session
    return session


def get_session(session_id: str) -> Session | None:
    return sessions.get(session_id.upper())


def add_idea(session_id: str, text: str, author: str) -> Idea | None:
    session = get_session(session_id)
    if not session or session.status != SessionStatus.ACTIVE:
        return None
    idea = Idea(text=text, author=author)
    session.ideas.append(idea)
    return idea
