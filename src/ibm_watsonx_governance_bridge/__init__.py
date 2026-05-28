"""ibm-watsonx-governance-bridge — gate watsonx.ai calls at the edge."""

from ibm_watsonx_governance_bridge.audit import emit_audit_event
from ibm_watsonx_governance_bridge.broker import Broker
from ibm_watsonx_governance_bridge.models import (
    Operation,
    Outcome,
    PermissionDecision,
    PermissionRequest,
    PolicyBundle,
    PolicyRule,
    TargetType,
)

__all__ = [
    "Broker",
    "Operation",
    "Outcome",
    "PermissionDecision",
    "PermissionRequest",
    "PolicyBundle",
    "PolicyRule",
    "TargetType",
    "emit_audit_event",
]
__version__ = "0.1.0"
