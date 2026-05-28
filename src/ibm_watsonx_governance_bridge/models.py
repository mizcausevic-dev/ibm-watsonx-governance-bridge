"""Policy and request models shared by the watsonx governance bridge."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Outcome = Literal["allow", "deny", "require_approval"]
TargetType = Literal["model", "deployment"]
Operation = Literal["text/chat", "text/generation"]


class PermissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caller_id: str = Field(..., description="Identity of the caller (app id, agent id, service principal).")
    tool_name: str = Field(
        ...,
        description="What is being invoked. e.g. 'watsonx.model.ibm/granite-3-8b-instruct' "
        "or 'tool.lookup_policy'.",
    )
    context: dict[str, Any] = Field(default_factory=dict)


class _Because(BaseModel):
    model_config = ConfigDict(extra="ignore")
    decision_card: str | None = None
    condition_id: str | None = None


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    priority: int = 0
    effect: Outcome
    tool_name: str = Field(default=".*", description="Regex matched against request.tool_name.")
    caller_id: str = Field(default=".*", description="Regex matched against request.caller_id.")
    when: dict[str, str] | None = Field(
        default=None, description="Optional {'expr': <python expression>} rule."
    )
    because: _Because | None = None


class PolicyBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    decision_card_url: str | None = None
    rules: list[PolicyRule] = Field(default_factory=list)


class PermissionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Outcome
    matched_rules: list[str] = Field(default_factory=list)
    decision_card_refs: list[str] = Field(default_factory=list)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rationale: str = ""
