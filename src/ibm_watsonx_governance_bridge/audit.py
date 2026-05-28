"""Best-effort audit-stream emitter for watsonx bridge decisions."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from ibm_watsonx_governance_bridge.models import (
    Operation,
    Outcome,
    PermissionDecision,
    PermissionRequest,
    TargetType,
)

logger = logging.getLogger(__name__)

_EVENT_KIND: dict[Outcome, str] = {
    "allow": "tool_invocation_allowed",
    "deny": "tool_invocation_denied",
    "require_approval": "tool_invocation_required_approval",
}

_SOURCE = "ibm-watsonx-governance-bridge"


def emit_audit_event(
    decision: PermissionDecision,
    request: PermissionRequest,
    *,
    audit_stream_url: str | None = None,
    client: httpx.Client | None = None,
) -> bool:
    """POST one governance event to audit-stream-py. Returns True if posted, False if skipped/failed."""
    url = audit_stream_url if audit_stream_url is not None else os.environ.get("AUDIT_STREAM_URL", "")
    if not url:
        return False

    event = {
        "kind": _EVENT_KIND[decision.outcome],
        "source": _SOURCE,
        "payload": {
            "correlation_id": decision.correlation_id,
            "caller_id": request.caller_id,
            "tool_name": request.tool_name,
            "matched_rules": decision.matched_rules,
            "decision_card_refs": decision.decision_card_refs,
            "rationale": decision.rationale,
            "context": request.context,
        },
    }

    try:
        response = client.post(url, json=event, timeout=2.0) if client is not None else httpx.post(
            url, json=event, timeout=2.0
        )
        if response.status_code >= 400:
            logger.warning("audit-stream POST returned HTTP %s", response.status_code)
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit-stream POST failed (best-effort, not raised): %s", exc)
        return False


def derive_tool_names(
    target_type: TargetType, target_id: str, operation: Operation, body: dict[str, Any]
) -> list[str]:
    """Turn a watsonx request into the list of tool_names to check."""
    names = [f"watsonx.{target_type}.{target_id}", f"watsonx.operation.{operation.replace('/', '.')}"]
    tools = body.get("tools")
    if isinstance(tools, list):
        for tool in tools:
            fn = tool.get("function") if isinstance(tool, dict) else None
            name = fn.get("name") if isinstance(fn, dict) else None
            if isinstance(name, str) and name:
                names.append(f"tool.{name}")
    return names
