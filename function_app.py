"""HTTP entry point for IBM watsonx governance bridge.

This bridge sits in front of watsonx.ai chat/text-generation endpoints and
enforces a buyer's AI Procurement Decision Card at request time.
"""

from __future__ import annotations

import json
import logging
import os

import httpx
from flask import Flask, Response, jsonify, request

from ibm_watsonx_governance_bridge.audit import emit_audit_event
from ibm_watsonx_governance_bridge.bridge import evaluate
from ibm_watsonx_governance_bridge.broker import Broker
from ibm_watsonx_governance_bridge.models import Operation, Outcome, TargetType
from ibm_watsonx_governance_bridge.upstream import build_upstream_request, get_bearer_token

logger = logging.getLogger("ibm_watsonx_governance_bridge")
app = Flask(__name__)


def _load_broker() -> Broker:
    raw = os.environ.get("POLICY_BUNDLES_JSON", "[]")
    default_outcome: Outcome = "deny" if os.environ.get("DEFAULT_OUTCOME", "deny") == "deny" else "allow"
    try:
        bundles = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("POLICY_BUNDLES_JSON is not valid JSON; defaulting to empty bundle set")
        bundles = []
    return Broker.from_dicts(bundles, default_outcome=default_outcome)


def _governed_request(target_type: TargetType, target_id: str, operation: Operation) -> Response:
    caller_id = request.headers.get("x-kg-caller-id", "anonymous")
    environment = request.headers.get("x-kg-environment", "production")

    try:
        body = request.get_json(force=True)
    except Exception:  # noqa: BLE001
        return jsonify({"error": "request body must be valid JSON"}), 400

    if not isinstance(body, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    broker = _load_broker()
    decision, perm_req = evaluate(
        broker,
        caller_id=caller_id,
        target_type=target_type,
        target_id=target_id,
        operation=operation,
        body=body,
        environment=environment,
    )
    emit_audit_event(decision, perm_req)

    if decision.outcome == "deny":
        return (
            jsonify(
                {
                    "error": "denied_by_governance",
                    "rationale": decision.rationale,
                    "matched_rules": decision.matched_rules,
                    "decision_card_refs": decision.decision_card_refs,
                    "correlation_id": decision.correlation_id,
                }
            ),
            403,
        )

    if decision.outcome == "require_approval":
        return (
            jsonify(
                {
                    "error": "approval_required",
                    "rationale": decision.rationale,
                    "matched_rules": decision.matched_rules,
                    "correlation_id": decision.correlation_id,
                }
            ),
            409,
        )

    try:
        upstream = build_upstream_request(
            target_type=target_type,
            target_id=target_id,
            operation=operation,
            body=body,
        )
        token = get_bearer_token()
        response = httpx.post(
            upstream.url,
            json=upstream.body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=60.0,
        )
    except RuntimeError as exc:
        return jsonify({"error": "bridge_misconfigured", "detail": str(exc)}), 500
    except Exception as exc:  # noqa: BLE001
        logger.error("upstream watsonx call failed: %s", exc)
        return jsonify({"error": "upstream_unreachable", "correlation_id": decision.correlation_id}), 502

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("content-type", "application/json"),
        headers={"x-kg-correlation-id": decision.correlation_id},
    )


@app.post("/api/governed/models/<path:model_id>/text/chat")
def governed_model_chat(model_id: str) -> Response:
    return _governed_request("model", model_id, "text/chat")


@app.post("/api/governed/models/<path:model_id>/text/generation")
def governed_model_generation(model_id: str) -> Response:
    return _governed_request("model", model_id, "text/generation")


@app.post("/api/governed/deployments/<deployment_id>/text/chat")
def governed_deployment_chat(deployment_id: str) -> Response:
    return _governed_request("deployment", deployment_id, "text/chat")


@app.post("/api/governed/deployments/<deployment_id>/text/generation")
def governed_deployment_generation(deployment_id: str) -> Response:
    return _governed_request("deployment", deployment_id, "text/generation")


@app.get("/api/healthz")
def healthz() -> Response:
    broker = _load_broker()
    return jsonify({"status": "ok", "bundles": broker.bundle_ids})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port)
