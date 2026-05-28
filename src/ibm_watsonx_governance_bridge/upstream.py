"""Upstream request helpers for IBM watsonx.ai."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, cast

import httpx

from ibm_watsonx_governance_bridge.models import Operation, TargetType

_TOKEN_CACHE: dict[str, float | str] = {"token": "", "expires_at": 0.0}


@dataclass
class UpstreamRequest:
    url: str
    body: dict[str, Any]


def get_bearer_token(*, client: httpx.Client | None = None) -> str:
    explicit = os.environ.get("IBM_CLOUD_IAM_TOKEN", "")
    if explicit:
        return explicit

    now = time.time()
    cached = _TOKEN_CACHE.get("token")
    expires_at = float(_TOKEN_CACHE.get("expires_at", 0.0))
    if isinstance(cached, str) and cached and now < expires_at - 60:
        return cached

    api_key = os.environ.get("IBM_CLOUD_API_KEY", "")
    if not api_key:
        raise RuntimeError("IBM_CLOUD_IAM_TOKEN or IBM_CLOUD_API_KEY must be configured")

    iam_url = os.environ.get("IBM_CLOUD_IAM_URL", "https://iam.cloud.ibm.com/identity/token")
    payload = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    response = (
        client.post(iam_url, data=payload, headers=headers, timeout=10.0)
        if client is not None
        else httpx.post(iam_url, data=payload, headers=headers, timeout=10.0)
    )
    response.raise_for_status()
    data = cast(dict[str, Any], response.json())
    token = cast(str, data["access_token"])
    expiry = float(data.get("expiration", now + int(data.get("expires_in", 3600))))
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = expiry
    return token


def build_upstream_request(
    *,
    target_type: TargetType,
    target_id: str,
    operation: Operation,
    body: dict[str, Any],
) -> UpstreamRequest:
    base = os.environ.get("WATSONX_BASE_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/")
    version = os.environ.get("WATSONX_VERSION", "2024-10-10")
    payload = dict(body)

    if target_type == "model":
        payload.setdefault("model_id", target_id)
        payload = _ensure_project_or_space(payload)
        url = f"{base}/ml/v1/{operation}?version={version}"
    else:
        url = f"{base}/ml/v1/deployments/{target_id}/{operation}?version={version}"

    return UpstreamRequest(url=url, body=payload)


def _ensure_project_or_space(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("project_id") or payload.get("space_id"):
        return payload
    project_id = os.environ.get("WATSONX_PROJECT_ID", "")
    space_id = os.environ.get("WATSONX_SPACE_ID", "")
    if project_id:
        payload["project_id"] = project_id
    elif space_id:
        payload["space_id"] = space_id
    return payload
