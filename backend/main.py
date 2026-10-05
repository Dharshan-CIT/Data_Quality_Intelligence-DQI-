"""FastAPI backend for Data Quality Intelligence.

Wraps dqi_core (unchanged, UI-independent) with a REST API plus one
multiplexed WebSocket per browser session used for three kinds of live
push: pipeline progress while a dataset is processed, a continuously
ticking streaming-simulation feed, and dataset-updated notifications after
remediation so the frontend never needs to poll.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.env_loader import load_env
load_env()

from backend.routers import datasets, results, impact, remediation, governance, reports, assistant
from backend.session_store import store
from backend.ws_manager import manager
from backend.pipeline_runner import stream_pipeline
from dqi_core.integrations.streaming import LocalSimulator, get_kafka_status

app = FastAPI(title="Data Quality Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev only — tighten before any real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(results.router)
app.include_router(impact.router)
app.include_router(remediation.router)
app.include_router(governance.router)
app.include_router(reports.router)
app.include_router(assistant.router)


@app.get("/api/health")
def health_check():
    return {"ok": True}


@app.get("/api/streaming/status")
def streaming_status():
    import os
    return get_kafka_status(os.environ.get("KAFKA_BOOTSTRAP_SERVERS"))


@app.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    session = store.get_or_create(session_id)
    await manager.connect(session_id, websocket)
    simulator = LocalSimulator()
    stream_task: asyncio.Task | None = None

    async def tick_loop():
        try:
            while True:
                metrics = simulator.tick(100)
                await manager.send(websocket, {
                    "type": "stream_tick",
                    "metrics": {
                        "mode": metrics.mode, "throughput_eps": metrics.throughput_eps,
                        "valid_events": metrics.valid_events, "malformed_events": metrics.malformed_events,
                        "schema_violations": metrics.schema_violations,
                        "quarantined_events": metrics.quarantined_events, "status": metrics.status,
                    },
                })
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            action = msg.get("action")

            if action == "run_pipeline":
                filename = msg.get("filename") or session.active_dataset
                if filename and filename in session.datasets:
                    await stream_pipeline(session.datasets[filename], lambda m: manager.send(websocket, m))
                else:
                    await manager.send(websocket, {"type": "error", "message": "Dataset not found."})

            elif action == "start_stream":
                if stream_task is None or stream_task.done():
                    stream_task = asyncio.create_task(tick_loop())

            elif action == "stop_stream":
                if stream_task is not None:
                    stream_task.cancel()
                    stream_task = None

    except WebSocketDisconnect:
        pass
    finally:
        if stream_task is not None:
            stream_task.cancel()
        await manager.disconnect(session_id, websocket)
