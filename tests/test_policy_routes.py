from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aegisai.main import app


def test_get_policy_json() -> None:
    with TestClient(app) as client:
        r = client.get("/v1/policy")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert "hybrid_allowed_labels" in data
        assert isinstance(data["hybrid_allowed_labels"], list)
        assert "force_local_only" in data


def test_force_local_only_rejects_hybrid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pol = tmp_path / "p.yaml"
    pol.write_text(
        "version: 1\nhybrid_allowed_labels: [public, internal]\nforce_local_only: true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AEGISAI_ROUTING_POLICY_PATH", str(pol))
    with TestClient(app) as client:
        r = client.get("/v1/policy")
        assert r.json().get("force_local_only") is True
        r2 = client.post(
            "/v1/jobs",
            json={
                "inputs": [{"type": "image_ref", "uri": "file:///tmp/x.png"}],
                "sensitivity_label": "internal",
                "mode": "hybrid",
            },
        )
        assert r2.status_code == 400
        assert "routing policy" in (r2.json().get("detail") or "").lower()
