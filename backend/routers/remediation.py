from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from backend.deps import get_session
from backend.serializers import dataset_summary, _clean
from backend.session_store import Session
from backend.ws_manager import manager
from dqi_core.remediation.engine import RemediationSession
from dqi_core.remediation.validation import build_validation_report

router = APIRouter(prefix="/api/remediation", tags=["remediation"])


def _state(session: Session, filename: Optional[str]):
    try:
        return session.require(filename)
    except KeyError:
        raise HTTPException(404, "No active dataset. Upload or load one first.")


def _ensure_session(state):
    if state.remediation_session is None:
        state.remediation_session = RemediationSession(state.original_df)
    return state.remediation_session


class MissingValuesRequest(BaseModel):
    column: str
    strategy: str
    constant: Optional[str] = None


class InvalidNumericRequest(BaseModel):
    column: str
    condition: str
    strategy: str
    replacement: Optional[float] = None


class ColumnRequest(BaseModel):
    column: str


def _action_dict(action):
    return _clean({
        "operation": action.operation, "column": action.column, "rows_affected": action.rows_affected,
        "reason": action.reason, "before_summary": action.before_summary, "after_summary": action.after_summary,
        "timestamp": action.timestamp,
    })


@router.get("/state")
def get_state(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    rsession = _ensure_session(state)
    return {
        "rows": len(rsession.current_df),
        "quarantine_rows": len(rsession.quarantine_df),
        "audit_trail": [_action_dict(a) for a in rsession.audit_trail],
    }


@router.post("/remove-duplicates")
def remove_duplicates(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    rsession = _ensure_session(state)
    action = rsession.remove_duplicate_rows()
    session.audit_log.log("remediation", state.filename, "duplicate_rows",
                           f"Removed {action.rows_affected} duplicate rows.")
    return _action_dict(action)


@router.post("/missing-values")
def handle_missing(req: MissingValuesRequest, filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    rsession = _ensure_session(state)
    try:
        action = rsession.handle_missing(req.column, req.strategy, constant=req.constant)
    except Exception as e:
        raise HTTPException(400, str(e))
    session.audit_log.log("remediation", state.filename, req.column,
                           f"{req.strategy} applied to missing values ({action.rows_affected} rows).")
    return _action_dict(action)


@router.post("/invalid-numeric")
def handle_invalid_numeric(req: InvalidNumericRequest, filename: Optional[str] = None,
                            session: Session = Depends(get_session)):
    state = _state(session, filename)
    rsession = _ensure_session(state)
    try:
        action = rsession.handle_invalid_numeric(req.column, req.condition, req.strategy, replacement=req.replacement)
    except Exception as e:
        raise HTTPException(400, str(e))
    session.audit_log.log("remediation", state.filename, req.column,
                           f"{req.strategy} applied to {req.condition} values ({action.rows_affected} rows).")
    return _action_dict(action)


@router.post("/normalize-formatting")
def normalize_formatting(req: ColumnRequest, filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    rsession = _ensure_session(state)
    action = rsession.normalize_formatting(req.column)
    session.audit_log.log("remediation", state.filename, req.column,
                           f"Formatting normalized ({action.rows_affected} rows changed).")
    return _action_dict(action)


@router.post("/normalize-dates")
def normalize_dates(req: ColumnRequest, filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    rsession = _ensure_session(state)
    action = rsession.normalize_dates(req.column)
    session.audit_log.log("remediation", state.filename, req.column,
                           f"Dates normalized ({action.rows_affected} rows changed).")
    return _action_dict(action)


@router.get("/quarantine")
def get_quarantine(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    rsession = _ensure_session(state)
    return {"rows": _clean(rsession.quarantine_df.to_dict(orient="records"))}


@router.post("/commit")
async def commit(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    rsession = _ensure_session(state)

    before_df = state.original_df
    before_health = state.health.overall
    before_issue_count = len(state.issues)

    state.current_df = rsession.current_df

    # recompute() already runs profiling + issue detection + pillars + health +
    # impact scoring + ranking in one pass — offload the whole pass to a worker
    # thread (it's pure pandas/numpy, no I/O) so a large dataset can't freeze
    # the event loop for every other request and the live websocket.
    def _recompute_and_validate():
        state.recompute()
        return build_validation_report(before_df, state.current_df, before_health, state.health.overall,
                                        before_issue_count, len(state.issues), state.profile.numeric_columns)

    report = await run_in_threadpool(_recompute_and_validate)
    state.validation_report = report
    session.record_snapshot(state)
    session.audit_log.log("remediation_commit", state.filename, "dataset",
                           f"Health {before_health} -> {state.health.overall}.")

    await manager.broadcast(session.session_id, {"type": "dataset_updated", "dataset": state.filename,
                                                  "summary": dataset_summary(state)})

    return {
        "dataset": dataset_summary(state),
        "validation": _clean({
            "rows_before": report.rows_before, "rows_after": report.rows_after,
            "missing_cells_before": report.missing_cells_before, "missing_cells_after": report.missing_cells_after,
            "health_before": report.health_before, "health_after": report.health_after,
            "issue_count_before": report.issue_count_before, "issue_count_after": report.issue_count_after,
            "ks_results": [r.__dict__ for r in report.ks_results],
        }),
    }
