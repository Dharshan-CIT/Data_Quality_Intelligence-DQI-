"""The DQI assistant.

If ANTHROPIC_API_KEY is set, an LLM-backed assistant can be wired in by the
caller (see app/pages — the hook point is `generate_llm_answer`), but by
default the assistant answers deterministically FROM THE ALREADY-COMPUTED
RESULTS ONLY. It never invents dataset statistics: every number it states
is read straight out of the HealthIndexResult / Issue / ranking objects
passed in.
"""
from __future__ import annotations

import os
from typing import List, Optional

from dqi_core.models import Issue


def llm_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _top_issue(issues: List[Issue]) -> Optional[Issue]:
    scored = [i for i in issues if i.impact_score is not None]
    if not scored:
        return None
    return max(scored, key=lambda i: i.impact_score)


def answer_question(question: str, health, issues: List[Issue], ranking_df=None) -> str:
    """Deterministic local assistant: pattern-matches the question to one of a
    handful of grounded templates, each filled only from computed results."""
    q = question.lower().strip()

    if "unhealthy" in q or "why is this dataset" in q or "health" in q:
        weakest = ", ".join(health.weakest)
        return (f"Overall health is {health.overall}/100 ({health.band}). "
                f"The weakest pillars are: {weakest}. See the Impact Analysis page for the issues "
                f"driving those scores down.")

    if "highest" in q and "impact" in q:
        top = _top_issue(issues)
        if not top:
            return "No scored issues are available yet — run Issue Detection and Impact Scoring first."
        return (f"The highest-impact issue is '{top.issue_type}' in column '{top.column}' "
                f"(impact score {top.impact_score}/100, severity {top.severity}/5, "
                f"affecting {top.affected_records} records, {top.frequency_pct}% of rows). {top.explanation}")

    if "column" in q and ("attention" in q or "worst" in q or "first" in q):
        top = _top_issue(issues)
        if not top or not top.column:
            return "No single column stands out — the highest-impact issue is dataset-wide."
        return f"Column '{top.column}' needs attention first — it drives the highest-impact issue currently detected."

    if "why" in q and "priority" in q:
        top = _top_issue(issues)
        if not top:
            return "No issues are scored yet."
        return (f"'{top.issue_type}' on '{top.column}' ranks #{top.impact_rank} by impact "
                f"(vs #{top.frequency_rank} by raw frequency) because its severity ({top.severity}/5) and "
                f"downstream sensitivity ({top.downstream_sensitivity}) outweigh how often it occurs alone.")

    if "remediat" in q or "recommend" in q:
        top = _top_issue(issues)
        if not top:
            return "No issues to remediate yet."
        return f"For the top-impact issue ('{top.issue_type}' on '{top.column}'): {top.recommended_action}"

    return ("I can answer questions about this dataset's computed health score, its weakest pillars, "
            "and which issue has the highest impact score — try asking 'what's the highest impact issue?' "
            "or 'why is this dataset unhealthy?'. I only use numbers already computed for this dataset; "
            "I don't have a general-purpose LLM connected (set ANTHROPIC_API_KEY to enable one).")
