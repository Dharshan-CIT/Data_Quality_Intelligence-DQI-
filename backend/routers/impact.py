from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from backend.deps import get_session
from backend.serializers import issues_list, ranking_list, rank_corr_dict
from backend.session_store import Session
from backend.ws_manager import manager
from dqi_core.impact.ranking import build_rankings
from dqi_core.impact.scoring import score_issues
from dqi_core.impact.stats import compute_rank_correlation
from dqi_core.business_impact import estimate_exposure, total_exposure
from dqi_core.rca import analyze_issue

router = APIRouter(prefix="/api/impact", tags=["impact"])


class ScoringConfig(BaseModel):
    critical_columns: list[str] = []
    revenue_per_record: float = 0.0
    operational_cost_per_record: float = 0.0


def _state(session: Session, filename: str | None):
    try:
        return session.require(filename)
    except KeyError:
        raise HTTPException(404, "No active dataset. Upload or load one first.")


@router.post("/rescore")
async def rescore(config: ScoringConfig, filename: str | None = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    state.critical_columns = config.critical_columns
    state.revenue_per_record = config.revenue_per_record
    state.operational_cost_per_record = config.operational_cost_per_record

    def _compute():
        issues = score_issues(state.issues, total_rows=len(state.current_df),
                               critical_columns=config.critical_columns,
                               revenue_per_record=config.revenue_per_record)
        ranking_df = build_rankings(issues)
        rank_corr = compute_rank_correlation(ranking_df)
        return issues, ranking_df, rank_corr

    # Rescoring/ranking is pure pandas work — offload it so it never blocks the
    # event loop (and therefore every other request/websocket) while it runs.
    state.issues, state.ranking_df, state.rank_corr = await run_in_threadpool(_compute)
    await manager.broadcast(session.session_id, {"type": "dataset_updated", "dataset": state.filename})
    return {"ranking": ranking_list(state), "correlation": rank_corr_dict(state)}


@router.get("/exposure")
async def get_exposure(filename: str | None = None, session: Session = Depends(get_session)):
    state = _state(session, filename)

    def _compute():
        exposures = estimate_exposure(state.issues, total_rows=len(state.current_df),
                                       revenue_per_record=state.revenue_per_record,
                                       operational_cost_per_record=state.operational_cost_per_record)
        return exposures, total_exposure(exposures)

    exposures, summary = await run_in_threadpool(_compute)
    return {
        "exposures": [{"issue_id": e.issue_id, "affected_records": e.affected_records,
                        "estimated_exposure": e.estimated_exposure, "risk_category": e.risk_category}
                       for e in exposures],
        "summary": summary,
    }


@router.get("/rca/{issue_id}")
def get_rca(issue_id: str, filename: str | None = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    issue = next((i for i in state.issues if i.issue_id == issue_id), None)
    if issue is None:
        raise HTTPException(404, "Issue not found.")
    rca = analyze_issue(issue)
    return rca.to_dict()
