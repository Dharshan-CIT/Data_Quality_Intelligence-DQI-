from typing import Optional

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from backend.deps import get_session
from backend.serializers import _clean, audit_log_list
from backend.session_store import Session
from dqi_core.governance.pii import detect_pii, tokenize_column
from dqi_core.governance.contracts import validate_against_contract, load_contract
from dqi_core.integrations.external_trackers import create_jira_ticket, trigger_pagerduty_alert

router = APIRouter(prefix="/api/governance", tags=["governance"])


def _state(session: Session, filename: Optional[str]):
    try:
        return session.require(filename)
    except KeyError:
        raise HTTPException(404, "No active dataset. Upload or load one first.")


@router.post("/pii/scan")
def scan_pii(filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    results = detect_pii(state.current_df)
    state.pii_results = results
    session.audit_log.log("pii_scan", state.filename, "dataset", f"{len(results)} pattern(s) found.")
    return _clean([{
        "column": r.column, "pattern": r.pattern, "match_count": r.match_count,
        "match_pct": r.match_pct, "sample_masked": r.sample_masked, "detection_method": r.detection_method,
    } for r in results])


class TokenizeRequest(BaseModel):
    column: str


@router.post("/pii/tokenize")
def tokenize(req: TokenizeRequest, filename: Optional[str] = None, session: Session = Depends(get_session)):
    state = _state(session, filename)
    state.current_df = tokenize_column(state.current_df, req.column)
    session.audit_log.log("tokenization", state.filename, req.column, "SHA-256 tokenized.")
    return {"ok": True}


@router.post("/contracts/validate")
async def validate_contract(filename: Optional[str] = None, use_example: bool = False,
                             contract_file: Optional[UploadFile] = File(None),
                             session: Session = Depends(get_session)):
    state = _state(session, filename)
    import os
    if use_example:
        example_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "contracts", "retail_sample_contract.yaml",
        )
        if not os.path.exists(example_path):
            raise HTTPException(404, "Example contract not found.")
        contract = load_contract(example_path)
        name = "retail_sample_contract.yaml"
    elif contract_file is not None:
        content = await contract_file.read()
        contract = yaml.safe_load(content)
        name = contract_file.filename
    else:
        raise HTTPException(400, "Provide a contract file or set use_example=true.")

    result = await run_in_threadpool(validate_against_contract, state.current_df, contract, name)
    state.contract_result = result
    session.audit_log.log("contract_validation", state.filename, name,
                           f"{result.deployment_status}: {len(result.violations)} violation(s).")
    return _clean(result.to_dict())


@router.get("/audit-log")
def get_audit_log(session: Session = Depends(get_session)):
    return audit_log_list(session)


INTEGRATION_ENV = {
    "jira": ["JIRA_BASE_URL", "JIRA_API_TOKEN"],
    "pagerduty": ["PAGERDUTY_ROUTING_KEY"],
}


@router.get("/integrations/status")
def integrations_status():
    import os
    result = {}
    for name, required in INTEGRATION_ENV.items():
        missing = [v for v in required if not os.environ.get(v)]
        result[name] = {"configured": not missing, "missing": missing, "required": required}
    return result


class ExternalRequest(BaseModel):
    summary: str


@router.post("/jira/create-ticket")
def jira_create(req: ExternalRequest):
    result = create_jira_ticket(req.summary, "Created from the DQI Governance page.")
    return result.__dict__


@router.post("/pagerduty/trigger")
def pagerduty_trigger(req: ExternalRequest):
    result = trigger_pagerduty_alert(req.summary)
    return result.__dict__
