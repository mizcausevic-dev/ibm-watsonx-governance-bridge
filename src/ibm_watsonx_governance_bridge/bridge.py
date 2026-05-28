"""Pure orchestration for watsonx policy evaluation."""

from __future__ import annotations

from typing import Any

from ibm_watsonx_governance_bridge.audit import derive_tool_names
from ibm_watsonx_governance_bridge.broker import Broker
from ibm_watsonx_governance_bridge.models import Operation, PermissionDecision, PermissionRequest, TargetType


def evaluate(
    broker: Broker,
    *,
    caller_id: str,
    target_type: TargetType,
    target_id: str,
    operation: Operation,
    body: dict[str, Any],
    environment: str = "production",
) -> tuple[PermissionDecision, PermissionRequest]:
    """Evaluate a watsonx request. Returns the governing decision and request."""
    context = {
        "environment": environment,
        "target_type": target_type,
        "target_id": target_id,
        "operation": operation,
        "project_id": body.get("project_id"),
        "space_id": body.get("space_id"),
    }
    tool_names = derive_tool_names(target_type, target_id, operation, body)

    decisions: list[tuple[PermissionDecision, PermissionRequest]] = []
    for tool_name in tool_names:
        request = PermissionRequest(caller_id=caller_id, tool_name=tool_name, context=context)
        decisions.append((broker.check(request), request))

    for outcome in ("deny", "require_approval"):
        for decision, request in decisions:
            if decision.outcome == outcome:
                return decision, request

    return decisions[0]
