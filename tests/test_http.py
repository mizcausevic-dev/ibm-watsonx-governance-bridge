from __future__ import annotations

import json

import function_app


def test_healthz_reports_loaded_bundles(monkeypatch) -> None:
    monkeypatch.setenv(
        "POLICY_BUNDLES_JSON",
        json.dumps([{"bundle_id": "bundle-a", "rules": [{"id": "allow-all", "effect": "allow"}]}]),
    )

    client = function_app.app.test_client()
    response = client.get("/api/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "bundles": ["bundle-a"]}


def test_denied_request_returns_403(monkeypatch) -> None:
    monkeypatch.setenv(
        "POLICY_BUNDLES_JSON",
        json.dumps(
            [
                {
                    "bundle_id": "bundle-a",
                    "decision_card_url": "https://example.com/card.json",
                    "rules": [
                        {
                            "id": "deny-all-prod-models",
                            "effect": "deny",
                            "tool_name": r"^watsonx\.model\..*",
                            "when": {"expr": "context.get('environment') == 'production'"},
                        },
                        {"id": "allow-ops", "effect": "allow", "tool_name": r"^watsonx\.operation\..*"},
                    ],
                }
            ]
        ),
    )

    client = function_app.app.test_client()
    response = client.post(
        "/api/governed/models/ibm/granite-3-8b-instruct/text/chat",
        headers={"x-kg-caller-id": "app-1", "x-kg-environment": "production"},
        json={"project_id": "proj-1", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["error"] == "denied_by_governance"
    assert payload["matched_rules"] == ["deny-all-prod-models"]


def test_allowed_request_forwards_upstream(monkeypatch) -> None:
    monkeypatch.setenv(
        "POLICY_BUNDLES_JSON",
        json.dumps([{"bundle_id": "bundle-a", "rules": [{"id": "allow-all", "effect": "allow"}]}]),
    )

    def fake_token() -> str:
        return "fake-token"

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}
        content = b'{"id":"resp-1","model_id":"ibm/granite-3-8b-instruct"}'

    captured: dict[str, object] = {}

    def fake_post(url: str, json: dict[str, object], headers: dict[str, str], timeout: float) -> FakeResponse:  # noqa: A002
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(function_app, "get_bearer_token", fake_token)
    monkeypatch.setattr(function_app.httpx, "post", fake_post)

    client = function_app.app.test_client()
    response = client.post(
        "/api/governed/models/ibm/granite-3-8b-instruct/text/chat",
        headers={"x-kg-caller-id": "app-1", "x-kg-environment": "staging"},
        json={"project_id": "proj-1", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 200
    assert response.headers["x-kg-correlation-id"]
    assert captured["url"] == "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2024-10-10"
    assert captured["json"]["model_id"] == "ibm/granite-3-8b-instruct"
    assert captured["headers"]["Authorization"] == "Bearer fake-token"
