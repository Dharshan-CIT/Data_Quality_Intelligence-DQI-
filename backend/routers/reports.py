import json
import os
import re
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from backend.deps import get_session
from backend.serializers import _clean
from backend.session_store import Session
from dqi_core.reporting import build_report, export_json, export_csv, export_pdf
from dqi_core.business_impact import estimate_exposure, total_exposure

router = APIRouter(prefix="/api/reports", tags=["reports"])

_REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports",
)


def _state(session: Session, filename: Optional[str]):
    try:
        return session.require(filename)
    except KeyError:
        raise HTTPException(404, "No active dataset. Upload or load one first.")


def _build(state, session):
    exposures = estimate_exposure(state.issues, total_rows=len(state.current_df),
                                   revenue_per_record=state.revenue_per_record,
                                   operational_cost_per_record=state.operational_cost_per_record)
    exposure_summary = total_exposure(exposures)
    return build_report(
        state.profile, state.health, state.pillars, state.ranking_df, state.rank_corr,
        validation_report=state.validation_report, exposure_summary=exposure_summary,
        contract_result=state.contract_result, pii_results=state.pii_results,
    )


@router.get("/summary")
def report_summary(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    report = _build(state, session)
    return report["executive_summary"]


SHARES_DIR = os.path.join(_REPORTS_DIR, "shares")
_SHARE_ID = re.compile(r"^[0-9a-f]{10}$")


@router.post("/share")
def create_share(filename: Optional[str] = None, session: Session = Depends(get_session)):
    """Freezes the current report into a read-only snapshot that anyone with the link can view."""
    state = _state(session, filename)
    report = _clean(_build(state, session))
    share_id = secrets.token_hex(5)
    os.makedirs(SHARES_DIR, exist_ok=True)
    with open(os.path.join(SHARES_DIR, f"{share_id}.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, default=str)
    session.audit_log.log("share", state.filename, "report", f"Shareable snapshot {share_id} created.")
    return {"id": share_id, "path": f"/share/{share_id}"}


@router.get("/shared/{share_id}")
def get_share(share_id: str):
    if not _SHARE_ID.match(share_id):
        raise HTTPException(404, "Shared report not found.")
    path = os.path.join(SHARES_DIR, f"{share_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Shared report not found.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@router.post("/export/json")
def export_report_json(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    report = _build(state, session)
    base = os.path.splitext(state.filename)[0]
    path = export_json(report, os.path.join(_REPORTS_DIR, f"{base}_report.json"))
    session.audit_log.log("export", state.filename, "report.json", path)
    return FileResponse(path, filename=f"{base}_report.json", media_type="application/json")


@router.post("/export/csv")
def export_report_csv(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    base = os.path.splitext(state.filename)[0]
    path = export_csv(state.ranking_df, os.path.join(_REPORTS_DIR, f"{base}_ranking.csv"))
    session.audit_log.log("export", state.filename, "ranking.csv", path)
    return FileResponse(path, filename=f"{base}_ranking.csv", media_type="text/csv")


@router.post("/export/pdf")
def export_report_pdf(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    report = _build(state, session)
    base = os.path.splitext(state.filename)[0]
    path = export_pdf(report, os.path.join(_REPORTS_DIR, f"{base}_report.pdf"))
    session.audit_log.log("export", state.filename, "report.pdf", path)
    return FileResponse(path, filename=f"{base}_report.pdf", media_type="application/pdf")
