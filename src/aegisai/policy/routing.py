from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RoutingPolicy(BaseModel):
    """
    Declares when hybrid (future cloud burst) is allowed.
    Phase 1 still executes locally; the API enforces eligibility only.
    """

    version: int = Field(default=1, ge=1)
    hybrid_allowed_labels: list[str] = Field(
        default_factory=lambda: ["public", "internal"],
        description="Labels for which mode=hybrid is accepted.",
    )
    force_local_only: bool = Field(
        default=False,
        description="If true, hybrid requests are always rejected.",
    )

    @model_validator(mode="after")
    def _labels_must_be_known(self) -> RoutingPolicy:
        known = {"public", "internal", "confidential", "regulated"}
        bad = [x for x in self.hybrid_allowed_labels if x not in known]
        if bad:
            raise ValueError(f"unknown sensitivity labels in hybrid_allowed_labels: {bad}")
        return self

    def allows_hybrid(self, sensitivity_label: str) -> bool:
        if self.force_local_only:
            return False
        return sensitivity_label in self.hybrid_allowed_labels

    def public_view(self) -> dict:
        return {
            "version": self.version,
            "hybrid_allowed_labels": list(self.hybrid_allowed_labels),
            "force_local_only": self.force_local_only,
        }
