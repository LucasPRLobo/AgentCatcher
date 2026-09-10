"""SQLAlchemy models for the session log — the schema shared by the honeypot,
the traffic harness and the classifier.

Invariant (see docs/architecture.md, docs/stack_plan.md): lure/canary hits live in
their own table so they are only ever labels and forensics, never classifier
features. ``site_version`` on every session keeps data from different decoy-site
iterations separable.
"""

from __future__ import annotations

import os
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

DEFAULT_DB_URL = "sqlite:///agentcatcher.db"


class Base(DeclarativeBase):
    pass


class Source(StrEnum):
    """How a session was generated. In collected data the source is known; in the
    wild it starts UNKNOWN and only lure contact proves AGENT (that proof is a label
    in :class:`LureHit`, never a feature)."""

    AGENT = "agent"
    HUMAN = "human"
    UNKNOWN = "unknown"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nanosecond epoch, to match Request.ts_ns; the middleware stamps time.time_ns().
    first_seen_ns: Mapped[int] = mapped_column(BigInteger)
    last_seen_ns: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[Source] = mapped_column(
        Enum(Source, native_enum=False, length=16), default=Source.UNKNOWN
    )
    # git commit of the decoy site the session hit; the site changes between experiments.
    site_version: Mapped[str] = mapped_column(String(64))

    requests: Mapped[list[Request]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Request.ts_ns"
    )
    lure_hits: Mapped[list[LureHit]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Request(Base):
    """One HTTP request, complete enough to reconstruct the session stream. Both the
    hand-crafted features and the sequence model are derived from this table."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    ts_ns: Mapped[int] = mapped_column(BigInteger, index=True)
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(2048), index=True)
    query: Mapped[str] = mapped_column(Text, default="")
    headers: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[int] = mapped_column(Integer)  # HTTP status code
    referrer: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Client IP, hashed with a secret salt before it is ever stored (AC-16 / AC-28).
    hash_ip: Mapped[str] = mapped_column(String(64), index=True)

    session: Mapped[Session] = relationship(back_populates="requests")


class LureHit(Base):
    """A session's contact with a lure / canary. LABEL AND FORENSICS ONLY — never read
    this table (or lure paths) from feature code (guarded by AC-35)."""

    __tablename__ = "lure_hits"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    lure_id: Mapped[str] = mapped_column(String(64))
    # Position of the first touch in the session's request stream — feeds detection latency.
    request_index: Mapped[int] = mapped_column(Integer)

    session: Mapped[Session] = relationship(back_populates="lure_hits")


class Run(Base):
    """Metadata for one scripted agent run. The session<->run link lives here, outside
    the request stream, so the classifier can never learn from it (AC-18)."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    framework: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    model_version: Mapped[str] = mapped_column(String(64))
    prompt_id: Mapped[str] = mapped_column(String(64))


def get_engine(url: str | None = None) -> Engine:
    """Engine for the session-log database. URL precedence: explicit arg, then
    ``AGENTCATCHER_DB_URL``, then a local SQLite file. SQLite runs with a single
    writer or WAL (see docs/stack_plan.md)."""

    return create_engine(url or os.environ.get("AGENTCATCHER_DB_URL", DEFAULT_DB_URL))


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
