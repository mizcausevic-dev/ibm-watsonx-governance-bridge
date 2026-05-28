# Changelog

## v1.0.0-prod — 2026-05-28
- Production hardening pass on Codex's v0.1-shipped scaffold. Confirmed `pytest`, `ruff check`, `mypy`, and the Pages workflow green on `main` at HEAD before tagging `v1.0-prod`.
- README hardened: added the standard `Production status` block (deploy / hardening / data posture / governance language) at the top of the doc, and appended the `Part of the Kinetic Gain Suite` SEO footer (descriptive dofollow anchors up to the suite hub + apex per `reference_seo_interlinking`).
- Governance language posture confirmed against the broadened `feedback_compliance_public_language` rule: frames as readiness / evidence / posture / controls / scaffolding across HIPAA · FERPA · SOC 2 · GDPR · ISO 27001 · accessibility · AI governance (NIST AI RMF, EU AI Act, ISO 42001). No "compliant" or "certified" overclaim language.
- Per the v2 repo-strategy matrix (Phase 0 anchor #1 — founder-credibility flagship), this repo is the IBM-native sibling of `azure-openai-governance-bridge` (Azure OpenAI) and `mcp-permission-broker` (MCP transport). Same primitive (request-time PolicyBundle enforcement), different upstream.
- Added to `procurement-pulse-engine/universe.csv` so the AI Procurement Pulse measures the watsonx surface from this issue forward.
- No `src/`, README narrative, docs, or screenshot edits — squad doctrine v1.1 respects the v0.1-shipped operator surface as Codex shipped it.

## v0.1-shipped - 2026-05-28

- Shipped `ibm-watsonx-governance-bridge` as a Python request-time governance bridge for IBM watsonx.ai.
- Added deny-trumps-allow `PolicyBundle` evaluation for model and deployment routes.
- Added IBM Cloud IAM bearer-token support with API-key exchange fallback.
- Added audit-stream event emission, correlation-id propagation, and Code Engine deployment scaffolding.
- Added tests covering rule evaluation, tool-name derivation, and audit emission.
