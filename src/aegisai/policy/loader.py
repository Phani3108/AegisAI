from __future__ import annotations

import logging
from pathlib import Path

import yaml

from aegisai.config import Settings
from aegisai.policy.routing import RoutingPolicy

logger = logging.getLogger(__name__)


def _default_policy_file() -> Path:
    # src/aegisai/policy/loader.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3] / "config" / "routing_policy.yaml"


def load_routing_policy(settings: Settings) -> RoutingPolicy:
    path = settings.routing_policy_path or _default_policy_file()
    if not path.is_file():
        logger.warning(
            "routing policy file not found at %s; using built-in defaults",
            path,
        )
        return RoutingPolicy()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw is None:
            raw = {}
        return RoutingPolicy.model_validate(raw)
    except Exception:
        logger.exception("failed to load routing policy from %s; using defaults", path)
        return RoutingPolicy()
