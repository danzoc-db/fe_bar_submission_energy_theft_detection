# Issues and Fixes

Technical errors, SDK quirks, and resolutions encountered during development.
Logged chronologically for future reference.

---

## Template

### Issue: [Short description]
**Date:** YYYY-MM-DD
**Phase:** [0/1/2/3/4]
**Severity:** [blocker/high/medium/low]

**Symptom:**
What happened.

**Root Cause:**
Why it happened.

**Fix:**
What resolved it.

**Prevention:**
How to avoid in future projects.

---

### Issue: APX build from git source fails — missing apx-agent binary
**Date:** 2026-03-17
**Phase:** 0c
**Severity:** blocker (workaround found)

**Symptom:**
`uvx --from git+https://github.com/databricks-solutions/apx.git apx init` fails with
`Error: "Missing apx-agent binary at .bins/agent/apx-agent-darwin-aarch64"`

**Root Cause:**
The APX Rust build requires a pre-compiled agent binary not included in the git source.

**Fix:**
Install APX via the custom PyPI index instead of building from source:
```toml
[dependency-groups]
dev = ["apx==0.2.6"]

[[tool.uv.index]]
name = "apx-index"
url = "https://databricks-solutions.github.io/apx/simple"
```
Then scaffold using `apx init` after `uv sync`.

**Prevention:**
Always install APX from the pre-built wheel index, never from git source.

---

### Issue: @types/react-plotly.js version mismatch
**Date:** 2026-03-17
**Phase:** 0c
**Severity:** low

**Symptom:**
`bun install` fails: `No version matching "^2.33.0" found for @types/react-plotly.js`

**Root Cause:**
Latest version is 2.6.4, not 2.33.0. The `^2.33.0` was an incorrect version.

**Fix:**
Changed to `"@types/react-plotly.js": "^2.6.0"` in package.json.

**Prevention:**
Always check actual version availability before specifying dependency versions.

---

### Issue: Databricks MCP connection failing — empty API response
**Date:** 2026-03-17
**Phase:** 1
**Severity:** blocker

**Symptom:**
All MCP tool calls fail with: `Failed to list SQL warehouses: Expecting value: line 1 column 1 (char 0)`

**Root Cause:**
The Databricks MCP server cannot authenticate to the workspace. The API returns
an empty response (not JSON), suggesting expired or missing OAuth token.

**Fix:**
Re-authenticate via CLI:
```bash
databricks auth login --profile DEFAULT
```
Or refresh the token if using OAuth.

**Prevention:**
Check `databricks auth env --profile DEFAULT` before starting MCP-dependent work.

---

### Issue: APX sidebar-user-footer requires /current-user endpoint
**Date:** 2026-03-17
**Phase:** 0c
**Severity:** medium

**Symptom:**
TypeScript error: `Module '"@/lib/api"' has no exported member 'useCurrentUserSuspense'`

**Root Cause:**
The APX scaffold's `sidebar-user-footer.tsx` expects a `/api/current-user` endpoint
with `operation_id="currentUser"` that returns `{user_name, display_name}`.

**Fix:**
Added `CurrentUserOut` response model and `/api/current-user` route to `router.py`.
Must have `response_model` for proper TypeScript type generation.

**Prevention:**
When using APX sidebar layout, always include the `/current-user` endpoint.
