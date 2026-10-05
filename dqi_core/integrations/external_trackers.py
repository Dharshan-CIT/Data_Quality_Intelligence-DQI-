"""Jira / PagerDuty integration interfaces.

Clean interface + honest "unavailable" fallback. Never fakes a successful
ticket creation or page. Wire up real credentials via environment variables
(JIRA_*, PAGERDUTY_*) to enable; until then every call returns
`ok=False` with a clear reason.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class IntegrationResult:
    ok: bool
    integration: str
    message: str
    reference: Optional[str] = None


def create_jira_ticket(summary: str, description: str) -> IntegrationResult:
    base_url = os.environ.get("JIRA_BASE_URL")
    token = os.environ.get("JIRA_API_TOKEN")
    if not base_url or not token:
        return IntegrationResult(
            ok=False, integration="jira",
            message="Jira integration unavailable: set JIRA_BASE_URL and JIRA_API_TOKEN to enable it.",
        )
    try:
        import requests  # local import: optional dependency
        resp = requests.post(
            f"{base_url}/rest/api/2/issue",
            json={"fields": {"summary": summary, "description": description,
                              "project": {"key": os.environ.get("JIRA_PROJECT_KEY", "DQI")},
                              "issuetype": {"name": "Bug"}}},
            headers={"Authorization": f"Bearer {token}"}, timeout=10,
        )
        if resp.status_code in (200, 201):
            key = resp.json().get("key")
            return IntegrationResult(ok=True, integration="jira", message="Ticket created.", reference=key)
        return IntegrationResult(ok=False, integration="jira",
                                  message=f"Jira API returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return IntegrationResult(ok=False, integration="jira", message=f"Jira request failed: {e}")


def trigger_pagerduty_alert(summary: str, severity: str = "warning") -> IntegrationResult:
    routing_key = os.environ.get("PAGERDUTY_ROUTING_KEY")
    if not routing_key:
        return IntegrationResult(
            ok=False, integration="pagerduty",
            message="PagerDuty integration unavailable: set PAGERDUTY_ROUTING_KEY to enable it.",
        )
    try:
        import requests
        resp = requests.post(
            "https://events.pagerduty.com/v2/enqueue",
            json={"routing_key": routing_key, "event_action": "trigger",
                  "payload": {"summary": summary, "severity": severity, "source": "DQI"}},
            timeout=10,
        )
        if resp.status_code == 202:
            return IntegrationResult(ok=True, integration="pagerduty", message="Alert triggered.",
                                      reference=resp.json().get("dedup_key"))
        return IntegrationResult(ok=False, integration="pagerduty",
                                  message=f"PagerDuty API returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        return IntegrationResult(ok=False, integration="pagerduty", message=f"PagerDuty request failed: {e}")
