"""Streams the already-computed pipeline stages as live progress events.

DatasetState.recompute() runs the full dqi_core pipeline synchronously (it's
fast — sub-second even on a few thousand rows), so by the time a dataset is
constructed every number already exists. This module doesn't recompute
anything; it replays those REAL results stage-by-stage over the websocket
with a small minimum display time per stage, so the UI can show "profiling
dataset... detecting issues... found 11..." the way a real pipeline run
would look, instead of everything appearing at once. No number here is
invented — every value sent is read directly off the DatasetState that was
actually computed.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from backend.session_store import DatasetState

Sender = Callable[[dict], Awaitable[None]]

STAGE_DELAY = 0.35  # seconds — purely for legibility of each stage in the UI


async def stream_pipeline(state: DatasetState, send: Sender):
    stages = [
        ("ingestion", "Ingesting file", {
            "rows": state.profile.rows, "columns": state.profile.columns,
            "memory_kb": round(state.profile.memory_bytes / 1024, 1),
        }),
        ("profiling", "Profiling dataset", {
            "missing_pct": state.profile.missing_pct, "duplicate_rows": state.profile.duplicate_rows,
            "numeric_columns": len(state.profile.numeric_columns),
            "categorical_columns": len(state.profile.categorical_columns),
        }),
        ("issue_detection", "Detecting quality issues", {
            "issue_count": len(state.issues),
            "critical_count": sum(1 for i in state.issues if i.severity >= 4),
        }),
        ("quality_pillars", "Scoring 10 quality pillars", {
            "weakest": state.health.weakest, "strongest": state.health.strongest,
        }),
        ("health_index", "Computing Dataset Health Index", {
            "overall": state.health.overall, "band": state.health.band,
        }),
        ("impact_scoring", "Scoring impact (severity x sensitivity x exposure)", {
            "top_impact": round(max((i.impact_score for i in state.issues if i.impact_score is not None), default=0.0), 2),
        }),
        ("ranking_stats", "Comparing frequency vs. impact rankings", {
            "spearman_rs": state.rank_corr.spearman_rs, "kendall_tau": state.rank_corr.kendall_tau,
            "n_issues": state.rank_corr.n,
        }),
    ]

    total = len(stages)
    for idx, (stage_id, label, detail) in enumerate(stages, start=1):
        await send({"type": "pipeline_progress", "stage": stage_id, "label": label,
                     "status": "running", "pct": round(100 * (idx - 1) / total, 1)})
        await asyncio.sleep(STAGE_DELAY)
        await send({"type": "pipeline_progress", "stage": stage_id, "label": label,
                     "status": "done", "pct": round(100 * idx / total, 1), "detail": detail})

    await send({
        "type": "pipeline_done", "dataset": state.filename,
        "summary": {
            "health": state.health.overall, "band": state.health.band,
            "issues": len(state.issues), "rows": state.profile.rows,
        },
    })
