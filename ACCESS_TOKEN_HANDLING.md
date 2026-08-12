# Access Token Handling Policy

**This document outlines the policy for handling Databricks Personal Access Tokens
(DAPI tokens) and other secrets in this repository.**

---

## Policy Summary

| Branch Type | Tokens Allowed? | Notes |
|-------------|-----------------|-------|
| **Feature branches** | Yes | Acceptable during development |
| **Main branch** | No | Must be redacted before merge |

---

## Guidelines

### During Development (Feature Branches)

When working on a feature branch, you **may** include Databricks tokens in local config
files for testing. Prefer keeping them out of Git entirely (see gitignored config below).

### Before Merging to Main

**Before creating a Pull Request to `main`**, you **must**:

1. **Replace all hardcoded tokens** with placeholders:
   ```bash
   export DATABRICKS_TOKEN="<YOUR_DATABRICKS_TOKEN>"
   ```
2. **Use environment variable references** where possible:
   ```python
   import os
   token = os.environ.get("DATABRICKS_TOKEN")
   ```
3. **Add setup instructions** pointing to secure authentication methods:
   ```bash
   databricks auth login --host https://your-workspace.cloud.databricks.com
   ```

---

## Security Scanning

This repository is monitored by **Drawbridge**, which scans for secrets across GitHub,
Jira, and Confluence. If a token is detected in the **main branch**, you will be
contacted to revoke the token and clean up the source.

**Note:** You only need to remove secrets from `main` - not from every branch.

---

## Recommended Authentication Methods

### 1. Gitignored Config File (Recommended for Local Dev)

The safest approach - tokens never get committed because the file is gitignored.

**Step 1:** Create a `.env.local` file (NOT committed):
```bash
# .env.local (gitignored - your actual secrets)
DATABRICKS_TOKEN=dapi1234567890abcdef...
DATABRICKS_HOST=https://adb-123456789.11.cloud.databricks.com
```

**Step 2:** Commit a template file that shows required variables:
```bash
# .env.template (committed)
DATABRICKS_TOKEN=<YOUR_DATABRICKS_TOKEN>
DATABRICKS_HOST=<YOUR_DATABRICKS_HOST>
```

**Step 3:** Confirm `.gitignore` covers local config (this repo already does):
```gitignore
.env.local
.env.*.local
*.local.env
config.local.*
secrets.json
secrets.yaml
.databrickscfg
```

**Step 4:** Load in your code:
```python
from dotenv import load_dotenv
import os

load_dotenv(".env.local")
token = os.environ.get("DATABRICKS_TOKEN")
```

### 2. Databricks CLI Authentication

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
# Token is stored securely in ~/.databrickscfg (gitignored)
```

### 3. Environment Variables

```bash
export DATABRICKS_TOKEN="your-token-here"
# Or pull from a secrets manager, e.g. 1Password:
export DATABRICKS_TOKEN=$(op read "op://Vault/Databricks/token")
```

### 4. Databricks Secret Scopes (for Databricks Apps & Notebooks)

```python
# In Databricks notebooks/apps, use secret scopes
token = dbutils.secrets.get(scope="my-scope", key="databricks-token")
```

For Databricks Apps, prefer service principal authentication - credentials are injected
automatically via `app.yaml` resource bindings, so no hardcoded tokens are needed.

This demo uses the following secret scopes:
- `energy-theft-fmapi` - PAT for FMAPI AI Gateway proxy
- `energy-theft-bedrock` - AWS credentials for Bedrock
- `energy-theft-gemini` - GCP credentials for Vertex AI (optional)

---

## Pre-Merge Checklist

Before merging to `main`, verify:

- [ ] No `dapi...` tokens in any files
- [ ] No other secrets (API keys, passwords) in code
- [ ] Config files use placeholders (`<YOUR_TOKEN>`)
- [ ] READMEs reference environment variables, not actual values
- [ ] Notebooks use `os.environ.get()` or `dbutils.secrets.get()` for credentials

### Quick Check Command

```bash
# From repository root
grep -rE "dapi[a-zA-Z0-9]{30,}" \
  --include="*.py" --include="*.md" --include="*.yaml" \
  --include="*.yml" --include="*.json" --include="*.ipynb" .
```

If any matches are found, replace them with placeholders before merging.

---

## What To Do If a Token Is Flagged

1. **Acknowledge** the security notification.
2. **Confirm revocation** - let the security team know it's safe to revoke centrally.
3. **Clean up** - remove the token from `main`.
4. **Generate a new token** for continued development.
5. **Use secure methods** - follow the authentication methods above going forward.

---

## Related Documentation

- [Databricks CLI Authentication](https://docs.databricks.com/en/dev-tools/cli/authentication.html)
- [Unity Catalog Secret Scopes](https://docs.databricks.com/en/security/secrets/secret-scopes.html)
- [Databricks Apps Authentication](https://docs.databricks.com/en/dev-tools/app-development.html)

---

**Policy Source:** Drawbridge Security Scanning Guidelines
