"""Pydantic DTOs for the session log — the in-memory / validation shapes used by the
logging middleware and the traffic tooling. Persistence lives in :mod:`agentcatcher.db`;
these mirror those tables, and both share the one :class:`~agentcatcher.db.Source` enum.
"""

from pydantic import BaseModel

from agentcatcher.db import Source

__all__ = ["Source", "RequestIn", "SessionIn", "LureHitIn", "RunIn"]


class RequestIn(BaseModel):
    session_id: int
    ts_ns: int
    method: str
    path: str
    query: str = ""
    headers: dict[str, str] = {}
    body: str = ""
    status: int  # HTTP status code
    referrer: str | None = None
    hash_ip: str


class SessionIn(BaseModel):
    first_seen_ns: int
    last_seen_ns: int
    source: Source = Source.UNKNOWN
    site_version: str


class LureHitIn(BaseModel):
    session_id: int
    lure_id: str
    request_index: int


class RunIn(BaseModel):
    session_id: int | None = None
    framework: str
    model: str
    model_version: str
    prompt_id: str
