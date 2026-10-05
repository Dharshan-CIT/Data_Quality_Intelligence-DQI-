"""Loads configs/weights.yaml once and exposes it with safe defaults.

Centralizing this means every scoring module reads the same, user-editable
assumptions instead of hard-coding numbers inline.
"""
from __future__ import annotations

import os
from functools import lru_cache

import yaml

_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "weights.yaml")

_FALLBACK = {
    "impact": {
        "severity": {"default_severity": 2},
        "downstream_sensitivity": {"default_sensitivity": 0.4, "critical_columns": []},
        "frequency_modifier_cap": 0.15,
    },
    "health_index": {
        "weights": {
            "completeness": 0.14, "uniqueness": 0.10, "validity": 0.14, "consistency": 0.10,
            "timeliness": 0.08, "accuracy": 0.10, "integrity": 0.12, "conformity": 0.10,
            "freshness": 0.08, "traceability": 0.04,
        },
        "bands": {"excellent": 90, "good": 75, "needs_attention": 55, "poor": 35},
    },
    "business_impact": {
        "default_revenue_per_record": 0.0,
        "default_operational_cost_per_record": 0.0,
        "impact_factor_by_severity": {5: 1.0, 4: 0.7, 3: 0.4, 2: 0.15, 1: 0.05},
    },
}


@lru_cache(maxsize=1)
def load_config(path: str = _DEFAULT_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        if not cfg:
            return _FALLBACK
        return cfg
    except FileNotFoundError:
        return _FALLBACK


def reload_config(path: str = _DEFAULT_PATH) -> dict:
    load_config.cache_clear()
    return load_config(path)
