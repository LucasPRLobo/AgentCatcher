import pytest
from fastapi.testclient import TestClient

from agentcatcher.honeypot.app import create_app


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_fastapi_default_docs_are_not_exposed(path):
    client = TestClient(create_app())
    assert client.get(path).status_code == 404
