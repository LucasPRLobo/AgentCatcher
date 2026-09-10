from agentcatcher.db import (
    Base,
    LureHit,
    Request,
    Run,
    Session,
    Source,
    get_engine,
    make_session_factory,
)


def _memory_factory():
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def test_session_stream_round_trips():
    factory = _memory_factory()
    with factory() as db:
        s = Session(first_seen_ns=1, last_seen_ns=3, source=Source.AGENT, site_version="abc123")
        s.requests = [
            Request(
                ts_ns=2,
                method="GET",
                path="/admin/",
                query="",
                headers={"user-agent": "curl/8.5.0"},
                body="",
                status=200,
                referrer=None,
                hash_ip="deadbeef",
            )
        ]
        s.lure_hits = [LureHit(lure_id="admin", request_index=0)]
        db.add(s)
        db.commit()
        sid = s.id

    with factory() as db:
        s = db.get(Session, sid)
        assert s.source is Source.AGENT
        assert s.site_version == "abc123"
        assert len(s.requests) == 1
        # headers survive as a JSON dict, not a string
        assert s.requests[0].headers == {"user-agent": "curl/8.5.0"}
        assert s.requests[0].status == 200
        assert s.lure_hits[0].lure_id == "admin"


def test_run_links_to_session_outside_request_stream():
    factory = _memory_factory()
    with factory() as db:
        s = Session(first_seen_ns=1, last_seen_ns=1, source=Source.AGENT, site_version="v1")
        db.add(s)
        db.flush()
        db.add(
            Run(
                session_id=s.id,
                framework="browser-use",
                model="claude-opus-5",
                model_version="2026-09",
                prompt_id="find-admin",
            )
        )
        db.commit()
        sid = s.id

    with factory() as db:
        run = db.query(Run).one()
        assert run.session_id == sid
        # the run<->session link is not a column on Request
        assert not hasattr(Request, "framework")
