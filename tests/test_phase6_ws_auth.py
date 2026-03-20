from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aegisai.main import app


def test_websocket_closed_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGISAI_API_KEY", "only-good-key")
    with TestClient(app) as client:
        # Handshake rejected when secret required but not sent
        with pytest.raises(Exception):
            with client.websocket_connect(
                "/v1/ws/jobs/00000000-0000-0000-0000-000000000001",
            ):
                pass


def test_websocket_accepts_x_api_key_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGISAI_API_KEY", "only-good-key")
    with TestClient(app) as client:
        with client.websocket_connect(
            "/v1/ws/jobs/00000000-0000-0000-0000-000000000001",
            headers={"X-API-Key": "only-good-key"},
        ) as ws:
            msg = ws.receive_json()
            assert msg.get("type") == "error"
            assert msg.get("detail") == "not_found"


def test_websocket_accepts_query_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGISAI_API_KEY", "qs-key")
    uri = "/v1/ws/jobs/00000000-0000-0000-0000-000000000001?api_key=qs-key"
    with TestClient(app) as client:
        with client.websocket_connect(uri) as ws:
            msg = ws.receive_json()
            assert msg.get("type") == "error"
