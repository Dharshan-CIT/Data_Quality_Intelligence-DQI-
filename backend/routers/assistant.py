from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.deps import get_session
from backend.session_store import Session
from dqi_core.assistant import answer_question, llm_available

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class Question(BaseModel):
    question: str


@router.get("/status")
def status():
    return {"llm_available": llm_available()}


@router.post("/ask")
def ask(q: Question, filename: Optional[str] = None, session: Session = Depends(get_session)):
    try:
        state = session.require(filename)
    except KeyError:
        raise HTTPException(404, "No active dataset. Upload or load one first.")
    answer = answer_question(q.question, state.health, state.issues, state.ranking_df)
    return {"answer": answer}
