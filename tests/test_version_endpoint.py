from __future__ import annotations

from fastapi.testclient import TestClient

from aegisai.main import app


def test_version_shape() -> None:
    with TestClient(app) as client:
        r = client.get("/version")
        assert r.status_code == 200
        data = r.json()
        assert data.get("name") == "aegisai"
        assert "version" in data and data["version"]
