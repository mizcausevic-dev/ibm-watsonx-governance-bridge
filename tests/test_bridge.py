from __future__ import annotations

import pytest

from ibm_watsonx_governance_bridge import Broker, PermissionRequest, PolicyBundle, PolicyRule
from ibm_watsonx_governance_bridge.audit import derive_tool_names, emit_audit_event
from ibm_watsonx_governance_bridge.bridge import evaluate

BUNDLE = {
    "bundle_id": "enterprise-watsonx-2026",
    "decision_card_url": "https://enterprise.example/.well-known/decisions/DEC-1.json",
    "rules": [
        {
            "id": "deny-prod-destructive-tools",
            "priority": 100,
            "effect": "deny",
            "tool_name": r"^tool\..*delete.*",
            "when": {"expr": "context.get('environment') == 'production'"},
        },
        {
            "id": "approval-for-sensitive-model",
            "priority": 90,
            "effect": "require_approval",
            "tool_name": r"^watsonx\.model\.meta-llama/llama-3-3-70b-instruct$",
            "caller_id": r"^untrusted-.*",
        },
        {
            "id": "allow-approved-models",
            "priority": 20,
            "effect": "allow",
            "tool_name": r"^watsonx\.model\..*",
            "caller_id": ".*",
        },
        {
            "id": "allow-governed-deployments",
            "priority": 10,
            "effect": "allow",
            "tool_name": r"^watsonx\.deployment\..*",
            "caller_id": ".*",
        },
        {
            "id": "allow-watsonx-operations",
            "priority": 9,
            "effect": "allow",
            "tool_name": r"^watsonx\.operation\..*",
            "caller_id": ".*",
        },
        {
            "id": "allow-tools-baseline",
            "priority": 5,
            "effect": "allow",
            "tool_name": r"^tool\..*",
            "caller_id": ".*",
        },
    ],
}


def make_broker(default: str = "deny") -> Broker:
    return Broker.from_dicts([BUNDLE], default_outcome=default)


def test_derive_tool_names_model_only() -> None:
    assert derive_tool_names("model", "ibm/granite-3-8b-instruct", "text/chat", {}) == [
        "watsonx.model.ibm/granite-3-8b-instruct",
        "watsonx.operation.text.chat",
    ]


def test_derive_tool_names_with_tools() -> None:
    body = {"tools": [{"function": {"name": "delete_record"}}, {"function": {"name": "search"}}]}
    assert derive_tool_names("deployment", "claims-assist", "text/chat", body) == [
        "watsonx.deployment.claims-assist",
        "watsonx.operation.text.chat",
        "tool.delete_record",
        "tool.search",
    ]


def test_allow_known_model_no_tools() -> None:
    broker = make_broker()
    decision, _ = evaluate(
        broker,
        caller_id="app-1",
        target_type="model",
        target_id="ibm/granite-3-8b-instruct",
        operation="text/chat",
        body={"project_id": "proj-1"},
    )
    assert decision.outcome == "allow"
    assert decision.matched_rules == ["allow-approved-models"]


def test_deny_trumps_allow_when_tool_is_destructive_in_prod() -> None:
    broker = make_broker()
    body = {"project_id": "proj-1", "tools": [{"function": {"name": "delete_record"}}]}
    decision, req = evaluate(
        broker,
        caller_id="app-1",
        target_type="deployment",
        target_id="claims-assist",
        operation="text/chat",
        body=body,
        environment="production",
    )
    assert decision.outcome == "deny"
    assert decision.matched_rules == ["deny-prod-destructive-tools"]
    assert req.tool_name == "tool.delete_record"


def test_destructive_tool_allowed_in_staging() -> None:
    broker = make_broker()
    body = {"project_id": "proj-1", "tools": [{"function": {"name": "delete_record"}}]}
    decision, _ = evaluate(
        broker,
        caller_id="app-1",
        target_type="deployment",
        target_id="claims-assist",
        operation="text/chat",
        body=body,
        environment="staging",
    )
    assert decision.outcome == "allow"


def test_untrusted_caller_requires_approval_for_sensitive_model() -> None:
    broker = make_broker()
    decision, _ = evaluate(
        broker,
        caller_id="untrusted-bot",
        target_type="model",
        target_id="meta-llama/llama-3-3-70b-instruct",
        operation="text/chat",
        body={"project_id": "proj-1"},
    )
    assert decision.outcome == "require_approval"
    assert decision.matched_rules == ["approval-for-sensitive-model"]


def test_default_deny_for_unknown_target_under_empty_bundle() -> None:
    broker = Broker.from_dicts([], default_outcome="deny")
    decision, _ = evaluate(
        broker,
        caller_id="app-1",
        target_type="model",
        target_id="mystery",
        operation="text/chat",
        body={"project_id": "proj-1"},
    )
    assert decision.outcome == "deny"
    assert decision.matched_rules == []


def test_decision_card_ref_propagates() -> None:
    broker = make_broker()
    decision, _ = evaluate(
        broker,
        caller_id="untrusted-bot",
        target_type="model",
        target_id="meta-llama/llama-3-3-70b-instruct",
        operation="text/chat",
        body={"project_id": "proj-1"},
    )
    assert decision.decision_card_refs == ["https://enterprise.example/.well-known/decisions/DEC-1.json"]


def test_emit_audit_noop_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUDIT_STREAM_URL", raising=False)
    broker = make_broker()
    decision, req = evaluate(
        broker,
        caller_id="app-1",
        target_type="model",
        target_id="ibm/granite-3-8b-instruct",
        operation="text/chat",
        body={"project_id": "proj-1"},
    )
    assert emit_audit_event(decision, req) is False


def test_emit_audit_posts_when_url_set() -> None:
    broker = make_broker()
    decision, req = evaluate(
        broker,
        caller_id="app-1",
        target_type="model",
        target_id="ibm/granite-3-8b-instruct",
        operation="text/chat",
        body={"project_id": "proj-1"},
    )

    posted: dict[str, object] = {}

    class FakeClient:
        def post(self, url: str, json: dict[str, object], timeout: float) -> object:  # noqa: A002
            posted["url"] = url
            posted["json"] = json

            class Response:
                status_code = 200

            return Response()

    ok = emit_audit_event(decision, req, audit_stream_url="http://localhost:8093/events", client=FakeClient())
    assert ok is True
    assert posted["url"] == "http://localhost:8093/events"
    assert posted["json"]["kind"] == "tool_invocation_allowed"
    assert posted["json"]["source"] == "ibm-watsonx-governance-bridge"


def test_when_expr_cannot_use_builtins() -> None:
    broker = Broker.from_dicts(
        [
            {
                "bundle_id": "b",
                "rules": [{"id": "x", "effect": "deny", "when": {"expr": "open('/etc/passwd')"}}],
            }
        ],
        default_outcome="allow",
    )
    decision = broker.check(
        PermissionRequest(caller_id="a", tool_name="watsonx.model.ibm/granite-3-8b-instruct")
    )
    assert decision.outcome == "allow"


def test_invalid_bundle_raises() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PolicyBundle.model_validate({"bundle_id": "x", "rules": "not a list"})


def test_policyrule_defaults() -> None:
    rule = PolicyRule(id="r", effect="allow")
    assert rule.tool_name == ".*"
    assert rule.caller_id == ".*"
