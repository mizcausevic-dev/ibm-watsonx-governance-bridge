# ibm-watsonx-governance-bridge

> A Python request-time governance bridge that sits in front of IBM watsonx.ai and **enforces a buyer's AI Procurement Decision Card on every chat or text-generation call**.

Point your app at the bridge instead of watsonx.ai directly:

```text
POST  https://<your-bridge>/api/governed/models/ibm/granite-3-8b-instruct/text/chat
      x-kg-caller-id: claims-assistant-prod
      x-kg-environment: production
```

The bridge evaluates the call against deny-trumps-allow `PolicyBundle`s, and:

- **allow** -> forwards to watsonx.ai, returns the upstream response verbatim (+ a `x-kg-correlation-id` header)
- **deny** -> `403` with the rationale and the Decision Card it traces to; nothing is forwarded
- **require_approval** -> `409`; the caller must obtain human approval first

Every decision emits a `tool_invocation_*` event to `audit-stream-py`, so the watsonx path writes to the same tamper-evident spine as the rest of the Kinetic Gain portfolio.

## Production status

| Aspect | Status |
|--------|--------|
| Deploy | Docs surface live at **https://watsonx.kineticgain.com/**; Code Engine deployment manifest in `infra/` |
| Hardening | `v1.0-prod` — CI (pytest, ruff, mypy) green on main; Pages workflow green; v0.1-shipped operator-surface preserved |
| Data posture | Synthetic Decision Cards, synthetic PolicyBundles, no IBM Cloud IAM credentials in repo; `local.settings.json` git-ignored |
| Governance language | Frames as readiness/evidence/posture per `feedback_compliance_public_language`; never "compliant" or "certified" |

## Why this exists

IBM and watsonx buyers need the same runtime governance primitive we already proved for Azure OpenAI and MCP: a Decision Card should not stop at review time. It should enforce at request time. This bridge brings that pattern to watsonx.ai with IBM Cloud IAM auth, model/deployment-aware routing, and correlation-id traceability.

## Why this matters (KG Embedded tie-back)

This repo is a Tier 4 Kinetic Gain Embedded proof surface: the same edge-gating primitive can become an embedded governance layer inside a client product, internal AI platform, or enterprise review workflow. The public repo shows the control plane and the request contract; the monetizable layer is the embedded, tenant-specific implementation. See [kineticgain.com/embedded](https://kineticgain.com/embedded).

## What gets checked

For each request the bridge derives a list of `tool_name`s and checks every one:

| Derived `tool_name` | From |
| --- | --- |
| `watsonx.model.<model_id>` | a foundation-model route such as `/api/governed/models/{model_id}/...` |
| `watsonx.deployment.<deployment_id>` | a deployment route such as `/api/governed/deployments/{deployment_id}/...` |
| `watsonx.operation.text.chat` | the chat endpoint |
| `watsonx.operation.text.generation` | the generation endpoint |
| `tool.<name>` | each function-calling tool declared in the request `tools[]` |

So a bundle can say "only Granite models in production," "sensitive models require approval," or "destructive tool calls are denied in prod" and the bridge enforces it before tokens are generated.

## Routes

- `POST /api/governed/models/{model_id}/text/chat`
- `POST /api/governed/models/{model_id}/text/generation`
- `POST /api/governed/deployments/{deployment_id}/text/chat`
- `POST /api/governed/deployments/{deployment_id}/text/generation`
- `GET /api/healthz`

## App settings

| Setting | Required | Purpose |
| --- | --- | --- |
| `WATSONX_BASE_URL` | no (`https://us-south.ml.cloud.ibm.com`) | watsonx.ai regional API base |
| `WATSONX_VERSION` | no (`2024-10-10`) | API version forwarded upstream |
| `IBM_CLOUD_IAM_TOKEN` | conditional | Pre-minted bearer token |
| `IBM_CLOUD_API_KEY` | conditional | Used to mint an IAM bearer token if no explicit token is present |
| `IBM_CLOUD_IAM_URL` | no (`https://iam.cloud.ibm.com/identity/token`) | IAM token endpoint |
| `POLICY_BUNDLES_JSON` | no (`[]`) | JSON array of PolicyBundle objects |
| `AUDIT_STREAM_URL` | no | audit-stream endpoint |
| `DEFAULT_OUTCOME` | no (`deny`) | Outcome when no rule matches |
| `WATSONX_PROJECT_ID` | optional | Default `project_id` injected for foundation-model routes |
| `WATSONX_SPACE_ID` | optional | Default `space_id` injected for foundation-model routes |

## Example request

```bash
curl -X POST http://localhost:8080/api/governed/models/ibm/granite-3-8b-instruct/text/chat \
  -H 'x-kg-caller-id: app-1' \
  -H 'x-kg-environment: production' \
  -H 'content-type: application/json' \
  -d '{"project_id":"proj-123","messages":[{"role":"user","content":"Summarize the policy"}]}'
```

## Local development

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
python function_app.py
```

Health:

```bash
curl http://localhost:8080/api/healthz
```

## Testing

```bash
pip install -e ".[dev]"
pytest -v
ruff check src tests function_app.py
mypy src
```

## Deploy

The code is shaped for IBM Code Engine or any HTTP container runtime. Keep the bridge read-only, inject IAM credentials through secrets, and never store tenant prompts or tokens in the repo.

## Composes with

| Concern | Repo |
| --- | --- |
| Azure sibling | [`azure-openai-governance-bridge`](https://github.com/mizcausevic-dev/azure-openai-governance-bridge) |
| MCP sibling | [`mcp-permission-broker`](https://github.com/mizcausevic-dev/mcp-permission-broker) |
| IBM connector packaging lane | [`ibm-custom-connector-starter`](https://github.com/mizcausevic-dev/ibm-custom-connector-starter) |
| Spec being enforced | `ai-procurement-decision-spec` / Decision Card derived PolicyBundles |

## License

AGPL-3.0-or-later.

## Part of the Kinetic Gain Suite

Operator surface in the [Kinetic Gain Suite](https://suite.kineticgain.com/) — a portfolio of buyer-readable control planes spanning security posture, compliance evidence, data-platform governance, FinOps, and operator workflows. See the suite index for related surfaces. Apex: [kineticgain.com](https://kineticgain.com/).
