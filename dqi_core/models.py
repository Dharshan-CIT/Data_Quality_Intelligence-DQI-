"""Shared structured result types used across the engine and the UI.

Keeping these as plain dataclasses (not pydantic/ORM models) means the engine
has zero dependency on any web framework, per the "dqi_core must stay
independent from the UI" rule.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Severity(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1


class HealthBand(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    NEEDS_ATTENTION = "Needs Attention"
    POOR = "Poor"
    CRITICAL = "Critical"


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    inferred_type: str  # numeric | categorical | datetime | boolean | text | identifier
    null_count: int
    null_pct: float
    unique_count: int
    uniqueness_ratio: float
    cardinality: str  # low | medium | high | unique
    min: Optional[Any] = None
    max: Optional[Any] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None
    outlier_count: Optional[int] = None
    suspicious_value_count: int = 0
    top_values: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DatasetProfile:
    filename: str
    rows: int
    columns: int
    memory_bytes: int
    duplicate_rows: int
    missing_cells: int
    missing_pct: float
    numeric_columns: list = field(default_factory=list)
    categorical_columns: list = field(default_factory=list)
    datetime_columns: list = field(default_factory=list)
    boolean_columns: list = field(default_factory=list)
    identifier_columns: list = field(default_factory=list)
    column_profiles: dict = field(default_factory=dict)  # name -> ColumnProfile
    profiled_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["column_profiles"] = {k: v.to_dict() if isinstance(v, ColumnProfile) else v
                                 for k, v in self.column_profiles.items()}
        return d


@dataclass
class PillarResult:
    name: str
    score: float  # 0-100
    affected_records: int
    affected_columns: list
    explanation: str
    detected_issues: list
    severity: str
    recommendations: list
    limitation: Optional[str] = None  # set when the pillar is a transparent proxy, not a direct measurement

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Issue:
    issue_id: str
    issue_type: str
    pillar: str
    column: Optional[str]
    affected_records: int
    frequency_pct: float
    severity: int  # 1-5
    explanation: str
    recommended_action: str
    evidence: dict = field(default_factory=dict)
    # populated later by the impact engine
    downstream_sensitivity: Optional[float] = None
    business_exposure: Optional[float] = None
    impact_score: Optional[float] = None
    impact_rank: Optional[int] = None
    frequency_rank: Optional[int] = None
    rank_change: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RemediationAction:
    operation: str
    column: Optional[str]
    rows_affected: int
    reason: str
    before_summary: dict
    after_summary: dict
    timestamp: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditEntry:
    timestamp: str
    action: str
    dataset: str
    affected_object: str
    result: str

    def to_dict(self) -> dict:
        return asdict(self)
