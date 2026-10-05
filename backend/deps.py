from fastapi import Header, HTTPException

from backend.session_store import store, Session


def get_session(x_session_id: str = Header(...)) -> Session:
    if not x_session_id:
        raise HTTPException(400, "Missing X-Session-Id header.")
    return store.get_or_create(x_session_id)
