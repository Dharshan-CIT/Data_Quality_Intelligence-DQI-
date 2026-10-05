import io
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.deps import get_session
from backend.serializers import dataset_summary
from backend.session_store import DatasetState, Session
from dqi_core.ingestion import load_file

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

_SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "sample", "retail_sample.csv",
)


@router.get("")
def list_datasets(session: Session = Depends(get_session)):
    return {
        "active": session.active_dataset,
        "datasets": [dataset_summary(s) for s in session.datasets.values()],
    }


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...), session: Session = Depends(get_session)):
    content = await file.read()

    def _ingest_and_build():
        result = load_file(io.BytesIO(content), file.filename)
        if not result.ok:
            return result, None
        return result, DatasetState(result.filename, result.dataframe)

    # Parsing + the full profile/issue-detection/scoring pipeline is pure
    # pandas/numpy work — run it off the event loop so a large upload can't
    # freeze every other request (and the live websocket) while it computes.
    result, state = await run_in_threadpool(_ingest_and_build)
    if not result.ok:
        raise HTTPException(422, result.error)

    session.datasets[result.filename] = state
    session.active_dataset = result.filename
    session.record_snapshot(state)
    session.audit_log.log("dataset_upload", result.filename, result.filename,
                           f"Loaded {result.dataframe.shape[0]} rows x {result.dataframe.shape[1]} columns.")
    return {"ok": True, "warnings": result.warnings, "dataset": dataset_summary(state)}


@router.get("/history")
def dataset_history(filename: str, session: Session = Depends(get_session)):
    return {"filename": filename, "snapshots": session.history.get(filename, [])}


@router.post("/load-sample")
def load_sample(session: Session = Depends(get_session)):
    result = load_file(_SAMPLE_PATH, "retail_sample.csv")
    if not result.ok:
        raise HTTPException(500, result.error)
    state = DatasetState(result.filename, result.dataframe)
    session.datasets[result.filename] = state
    session.active_dataset = result.filename
    session.record_snapshot(state)
    session.audit_log.log("dataset_upload", result.filename, result.filename,
                           f"Loaded sample dataset ({result.dataframe.shape[0]} rows).")
    return {"ok": True, "dataset": dataset_summary(state)}


@router.post("/active/{filename}")
def set_active(filename: str, session: Session = Depends(get_session)):
    if filename not in session.datasets:
        raise HTTPException(404, "Dataset not found in this session.")
    session.active_dataset = filename
    return {"ok": True, "active": filename}


@router.delete("/{filename}")
def delete_dataset(filename: str, session: Session = Depends(get_session)):
    if filename not in session.datasets:
        raise HTTPException(404, "Dataset not found.")
    del session.datasets[filename]
    if session.active_dataset == filename:
        session.active_dataset = next(iter(session.datasets), None)
    return {"ok": True}
