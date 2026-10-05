"""Real-time / streaming architecture.

Kafka is OPTIONAL. If `kafka-python` is importable AND a bootstrap server is
reachable, `KafkaPipeline` streams real events. Otherwise the app runs
`LocalSimulator`, which generates synthetic events and is always, visibly
labeled "Simulation Mode" wherever it's displayed. Simulated metrics are
never presented as if they came from a real broker.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PipelineMetrics:
    mode: str  # "simulation" | "kafka"
    throughput_eps: float
    valid_events: int
    malformed_events: int
    schema_violations: int
    quarantined_events: int
    status: str


class LocalSimulator:
    """Generates synthetic events locally — no network calls, no fake success claims."""

    def __init__(self, malformed_rate: float = 0.05, violation_rate: float = 0.03, seed: int = 42):
        self._rng = random.Random(seed)
        self.malformed_rate = malformed_rate
        self.violation_rate = violation_rate
        self.valid_events = 0
        self.malformed_events = 0
        self.schema_violations = 0
        self.quarantined_events = 0
        self._start = time.time()

    def tick(self, n_events: int = 100) -> PipelineMetrics:
        for _ in range(n_events):
            r = self._rng.random()
            if r < self.malformed_rate:
                self.malformed_events += 1
                self.quarantined_events += 1  # circuit breaker: malformed -> quarantine, never propagated
            elif r < self.malformed_rate + self.violation_rate:
                self.schema_violations += 1
                self.quarantined_events += 1
            else:
                self.valid_events += 1
        elapsed = max(time.time() - self._start, 1e-6)
        total = self.valid_events + self.malformed_events + self.schema_violations
        return PipelineMetrics(
            mode="simulation", throughput_eps=round(total / elapsed, 2),
            valid_events=self.valid_events, malformed_events=self.malformed_events,
            schema_violations=self.schema_violations, quarantined_events=self.quarantined_events,
            status="SIMULATION MODE — synthetic events, not a live broker.",
        )


def get_kafka_status(bootstrap_servers: Optional[str] = None) -> dict:
    """Checks whether a real Kafka integration is actually usable right now.
    Never claims success it hasn't verified."""
    try:
        import kafka  # noqa: F401
    except ImportError:
        return {"available": False, "reason": "kafka-python is not installed. Running in Simulation Mode."}

    if not bootstrap_servers:
        return {"available": False, "reason": "No KAFKA_BOOTSTRAP_SERVERS configured. Running in Simulation Mode."}

    try:
        from kafka import KafkaAdminClient
        client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, request_timeout_ms=2000)
        client.close()
        return {"available": True, "reason": f"Connected to Kafka at {bootstrap_servers}."}
    except Exception as e:
        return {"available": False, "reason": f"Kafka configured but unreachable: {e}. Running in Simulation Mode."}
