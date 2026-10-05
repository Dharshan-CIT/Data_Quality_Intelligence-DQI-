import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.deps import get_session
from backend.serializers import (
    profile_dict, pillars_dict, health_dict, issues_list, ranking_list, rank_corr_dict,
)
from backend.session_store import Session
from backend.ws_manager import manager
from dqi_core.health import compute_health_index

router = APIRouter(prefix="/api/results", tags=["results"])


def _state(session: Session, filename: str | None):
    try:
        return session.require(filename)
    except KeyError:
        raise HTTPException(404, "No active dataset. Upload or load one first.")


@router.get("/profile")
def get_profile(filename: str | None = None, session: Session = Depends(get_session)):
    return profile_dict(_state(session, filename))


@router.get("/pillars")
def get_pillars(filename: str | None = None, session: Session = Depends(get_session)):
    return pillars_dict(_state(session, filename))


@router.get("/health")
def get_health(filename: str | None = None, session: Session = Depends(get_session)):
    return health_dict(_state(session, filename))


class HealthWeights(BaseModel):
    weights: dict[str, float]


@router.post("/health/weights")
async def set_health_weights(req: HealthWeights, filename: str | None = None, session: Session = Depends(get_session)):
    """Re-weights the 10 pillars and recomputes the health index. Weights are normalised by their sum."""
    state = _state(session, filename)
    unknown = set(req.weights) - set(state.pillars)
    if unknown:
        raise HTTPException(400, f"Unknown pillar(s): {', '.join(sorted(unknown))}")
    if any(w < 0 for w in req.weights.values()) or sum(req.weights.values()) <= 0:
        raise HTTPException(400, "Weights must be non-negative and sum to more than zero.")
    state.health_weights = {name: float(req.weights.get(name, 0.0)) for name in state.pillars}
    state.health = compute_health_index(state.pillars, weights=state.health_weights)
    session.audit_log.log("health_weights", state.filename, "dataset", f"Health index re-weighted: {state.health.overall}.")
    await manager.broadcast(session.session_id, {"type": "dataset_updated", "dataset": state.filename})
    return health_dict(state)


@router.get("/bin-rows")
def get_bin_rows(column: str, bin: int, bins: int = 60, filename: str | None = None,
                 limit: int = 100, session: Session = Depends(get_session)):
    """Rows behind one cell of the missing-value heatmap, rows missing `column` first."""
    state = _state(session, filename)
    df = state.current_df
    if column not in df.columns:
        raise HTTPException(404, "Column not found.")
    n = len(df)
    bins = max(1, min(bins, n or 1))
    if not 0 <= bin < bins:
        raise HTTPException(400, f"bin must be between 0 and {bins - 1}.")
    edges = np.linspace(0, n, bins + 1).astype(int)
    lo, hi = int(edges[bin]), int(edges[bin + 1])
    segment = df.iloc[lo:hi]
    null_mask = segment.isna()
    order = np.argsort(~null_mask[column].to_numpy(), kind="stable")[:limit]
    picked = segment.iloc[order]
    rows = []
    for pos, (idx, record) in zip(order, picked.iterrows()):
        values = {c: _jsonable(v) for c, v in record.items()}
        rows.append({
            "row": int(lo + pos),
            "index": _jsonable(idx),
            "values": values,
            "null_columns": [c for c in df.columns if null_mask.iloc[pos][c]],
        })
    return {
        "column": column, "bin": bin, "bins": bins, "row_range": [lo, hi],
        "rows_in_bin": hi - lo, "null_in_column": int(null_mask[column].sum()),
        "shown": len(rows), "rows": rows,
    }


def _jsonable(v):
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if pd.isna(v) else float(v)
    if pd.isna(v):
        return None
    return str(v)


@router.get("/issues")
def get_issues(filename: str | None = None, session: Session = Depends(get_session)):
    return issues_list(_state(session, filename))


@router.get("/ranking")
def get_ranking(filename: str | None = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    return {"ranking": ranking_list(state), "correlation": rank_corr_dict(state)}


@router.get("/missing-matrix")
def get_missing_matrix(filename: str | None = None, bins: int = 60, session: Session = Depends(get_session)):
    import numpy as np
    state = _state(session, filename)
    df = state.current_df
    cols = list(df.columns)[:20]
    n = len(df)
    bins = max(1, min(bins, n or 1))
    edges = np.linspace(0, n, bins + 1).astype(int)
    matrix = []
    null_mask = df[cols].isna().to_numpy()
    for c_idx in range(len(cols)):
        col_vals = []
        for b in range(bins):
            lo, hi = edges[b], edges[b + 1]
            seg = null_mask[lo:hi, c_idx] if hi > lo else np.array([False])
            col_vals.append(round(float(seg.mean()), 4))
        matrix.append(col_vals)
    return {"columns": cols, "bins": bins, "rows": n, "matrix": matrix}
