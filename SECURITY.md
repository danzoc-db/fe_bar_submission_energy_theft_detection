# Security Policy

## Scope

This is a **Databricks Field Engineering demo** application. It is not a production product and is not intended for use with real customer data. The demo uses synthetic / sample energy consumption data only.

## Supported Versions

Only the latest commit on the `main` branch is actively maintained.

| Branch | Supported |
|--------|-----------|
| `main` (latest) | Yes |
| All other branches | No |

## Reporting a Vulnerability

If you discover a security issue in this demo:

1. **Do not** open a public GitHub issue.
2. Email **security@databricks.com** with subject line `[Demo] UKI Gas Energy Theft Detection — Security Issue`.
3. Include a description of the issue, reproduction steps, and potential impact.

You can expect an acknowledgement within 5 business days. As this is a demo, remediation timelines are best-effort.

## Secrets and Credentials

- No real customer credentials are stored in this repository.
- `.env.*` files are gitignored; do not commit them.
- Databricks Personal Access Tokens (PATs) and cloud provider credentials must be stored in Databricks Secret Scopes, not in code or environment files checked in to version control.
- The `energy-theft-fmapi` secret scope holds the PAT used by the FMAPI AI Gateway proxy. Rotate it if you believe it has been compromised.

## Demo-Only Notice

This application is built for demonstration purposes. It should run in an isolated Databricks workspace and should not be connected to production Unity Catalog data, production SQL warehouses, or live customer systems.
