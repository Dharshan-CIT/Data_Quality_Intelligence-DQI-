"""Append-only audit log for every significant platform action.

In-memory for the Streamlit session (st.session_state holds the instance),
with optional JSON persistence to reports/audit_log.json so a session's
trail survives a restart if the user chooses to export it.
"""
from __future__ import annotations

import json
import os
from typing import List

from dqi_core.models import AuditEntry, utcnow_iso


class AuditLog:
    def __init__(self):
        self.entries: List[AuditEntry] = []

    def log(self, action: str, dataset: str, affected_object: str, result: str) -> AuditEntry:
        entry = AuditEntry(timestamp=utcnow_iso(), action=action, dataset=dataset,
                            affected_object=affected_object, result=result)
        self.entries.append(entry)
        return entry

    def as_dataframe(self):
        import pandas as pd
        if not self.entries:
            return pd.DataFrame(columns=["timestamp", "action", "dataset", "affected_object", "result"])
        return pd.DataFrame([e.to_dict() for e in self.entries])

    def export_json(self, path: str) -> str:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self.entries], f, indent=2)
        return path
