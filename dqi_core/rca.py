"""Rule-based root-cause analysis.

Distinguishes DETECTED EVIDENCE (directly measured from the data, e.g. "32%
of this column fails numeric parsing") from INFERRED EXPLANATION (a
plausible cause we cannot verify from this dataset alone, e.g. "likely a
free-text form field upstream"). The UI must render these as two separate
labeled sections — never merge speculation into fact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from dqi_core.models import Issue

_CAUSE_RULES = {
    "missing_values": {
        "probable_source": "Upstream form/API allows an optional or unvalidated field.",
        "contributing_factors": ["No NOT NULL constraint at source", "Optional field in UI/API",
                                  "ETL join producing unmatched rows"],
    },
    "duplicate_row": {
        "probable_source": "Re-ingestion or retry logic without deduplication.",
        "contributing_factors": ["At-least-once delivery without idempotency key",
                                  "Multiple ingestion jobs writing the same batch"],
    },
    "duplicate_primary_key": {
        "probable_source": "Key-generation collision or merge of two independently keyed systems.",
        "contributing_factors": ["Non-atomic ID generation", "Manual data merge/migration"],
    },
    "invalid_numeric_range": {
        "probable_source": "Unvalidated numeric input or unit/sign conversion error.",
        "contributing_factors": ["Missing range validation at entry", "Currency/unit conversion bug",
                                  "Refund/adjustment rows misencoded as negative"],
    },
    "outlier_extreme": {
        "probable_source": "Data entry error, sensor fault, or a legitimate rare event.",
        "contributing_factors": ["Manual entry typo (extra digit)", "Unit mismatch (e.g. cents vs dollars)"],
    },
    "formatting_inconsistency": {
        "probable_source": "Multiple entry channels (manual + API + import) without shared normalization.",
        "contributing_factors": ["No shared enum/lookup table", "Free-text entry instead of a dropdown"],
    },
    "schema_violation": {
        "probable_source": "Column changed meaning/type upstream, or free text leaking into a typed field.",
        "contributing_factors": ["Upstream schema change not propagated", "CSV export encoding/locale mismatch"],
    },
    "invalid_date": {
        "probable_source": "Inconsistent date format across source systems (locale, separators).",
        "contributing_factors": ["Mixed MM/DD/YYYY vs DD/MM/YYYY sources", "Free-text date entry"],
    },
    "future_date": {
        "probable_source": "Clock/timezone misconfiguration or manual entry error.",
        "contributing_factors": ["Client-side clock skew", "Timezone offset applied twice"],
    },
    "stale_record": {
        "probable_source": "Upstream sync job stopped running or is silently failing for a subset of records.",
        "contributing_factors": ["Broken incremental sync cursor", "Partial pipeline failure"],
    },
}

_DEFAULT_CAUSE = {
    "probable_source": "Not enough signal in this dataset alone to infer a specific upstream cause.",
    "contributing_factors": [],
}


@dataclass
class RootCauseResult:
    issue_id: str
    detected_evidence: str
    probable_source: str
    contributing_factors: List[str]
    propagation_chain: List[str] = field(default_factory=list)
    downstream_consequence: str = ""

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id, "detected_evidence": self.detected_evidence,
            "probable_source": self.probable_source, "contributing_factors": self.contributing_factors,
            "propagation_chain": self.propagation_chain, "downstream_consequence": self.downstream_consequence,
        }


def analyze_issue(issue: Issue) -> RootCauseResult:
    cause = _CAUSE_RULES.get(issue.issue_type, _DEFAULT_CAUSE)
    column_label = issue.column or "(dataset-wide)"
    propagation_chain = [
        f"Source / upstream event ({'INFERRED' if cause is not _DEFAULT_CAUSE else 'UNKNOWN'})",
        f"Data layer: column '{column_label}'",
        f"Quality issue: {issue.issue_type} (DETECTED — {issue.affected_records} records, "
        f"{issue.frequency_pct}%)",
        f"Affected feature: '{column_label}' and anything joined/derived from it",
        f"Downstream impact: {issue.recommended_action}",
    ]
    return RootCauseResult(
        issue_id=issue.issue_id,
        detected_evidence=issue.explanation,
        probable_source=cause["probable_source"],
        contributing_factors=cause["contributing_factors"],
        propagation_chain=propagation_chain,
        downstream_consequence=issue.recommended_action,
    )


def analyze_all(issues: List[Issue]) -> List[RootCauseResult]:
    return [analyze_issue(i) for i in issues]
