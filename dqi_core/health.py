"""Dataset Health Index: a transparent weighted combination of the 10 pillars."""
from __future__ import annotations

from dataclasses import dataclass, field

from dqi_core.config import load_config


@dataclass
class HealthIndexResult:
    overall: float
    band: str
    pillar_scores: dict
    weakest: list
    strongest: list
    weights_used: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "overall": self.overall, "band": self.band, "pillar_scores": self.pillar_scores,
            "weakest": self.weakest, "strongest": self.strongest, "weights_used": self.weights_used,
        }


def _band(score: float, bands: dict) -> str:
    if score >= bands.get("excellent", 90):
        return "Excellent"
    if score >= bands.get("good", 75):
        return "Good"
    if score >= bands.get("needs_attention", 55):
        return "Needs Attention"
    if score >= bands.get("poor", 35):
        return "Poor"
    return "Critical"


def compute_health_index(pillar_results: dict, weights: dict | None = None) -> HealthIndexResult:
    cfg = load_config()["health_index"]
    weights = weights or cfg["weights"]
    pillar_scores = {name: result.score for name, result in pillar_results.items()}

    total_weight = sum(weights.get(name, 0) for name in pillar_scores) or 1.0
    overall = sum(pillar_scores[name] * weights.get(name, 0) for name in pillar_scores) / total_weight
    overall = round(overall, 2)

    ranked = sorted(pillar_scores.items(), key=lambda kv: kv[1])
    weakest = [name for name, _ in ranked[:3]]
    strongest = [name for name, _ in ranked[-3:]][::-1]

    return HealthIndexResult(
        overall=overall, band=_band(overall, cfg["bands"]), pillar_scores=pillar_scores,
        weakest=weakest, strongest=strongest, weights_used=weights,
    )
