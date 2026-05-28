# Security Policy

`ibm-watsonx-governance-bridge` is a request-time enforcement layer for watsonx.ai calls. It evaluates PolicyBundles, forwards allowed requests upstream, and adds a correlation id to every response. It does not ship tenant prompts, production model payloads, or static credentials in the repository.

## Reporting a Vulnerability

Please do not open public issues for sensitive reports.

- Open a GitHub security advisory for this repository.
- Or use the maintainer security contact route already established for Kinetic Gain work.

Include:

- affected route or package area
- reproduction steps
- expected vs actual behavior
- whether the issue impacts policy evaluation, IAM token handling, or upstream forwarding

## Data Handling Notes

- Sample policy bundles are synthetic.
- The bridge is intended for read-only governance enforcement with least-privilege credentials injected through environment variables or secrets.
- Do not store real IBM Cloud API keys, bearer tokens, prompts, or production request bodies in this repository.
