# AI-Assisted Coding - Gotchas & Best Practices

When using AI coding assistants (Cursor, Claude Code, GitHub Copilot, etc.) for
"vibe coding" in this repo, be aware of these common pitfalls. AI is great for
productivity, but **you** are responsible for code quality, security, and Git hygiene.

## Branch Management Issues

### 1. Wrong Branch Creation

- AI tools may create branches without checking you're starting from `main`.
- **Always verify:** Run `git branch` to confirm you're on `main` before creating a feature branch.
- **Manual fix:** If you branched from the wrong base:
  ```bash
  git checkout feat/your-work
  git rebase --onto main <wrong-base-branch> feat/your-work
  ```

### 2. Stale Base Branch

- AI may create a branch when your local `main` is outdated.
- **Always verify:** Pull latest `main` before branching: `git pull origin main`.

### 3. Branch Name Inconsistencies

- AI might suggest branch names that don't follow our convention.
- **Always verify:** Names must match `feat/` or `fix/` prefix and be lowercase.
- **Manual fix:** Rename locally and update remote:
  ```bash
  git branch -m old-name new-name
  git push origin :old-name new-name
  git push origin -u new-name
  ```

## Commit and PR Issues

### 4. Excessive Commit Messages

- AI iterations can create dozens of micro-commits ("fix typo", "update", "fix again").
- **Don't worry:** We use squash-merge, so these get consolidated.
- **Best practice:** Write a meaningful PR title and description - that becomes the final commit message.

### 5. Untracked Changes

- AI may generate or modify files without adding them to Git.
- **Always verify:** Run `git status` before committing.
- **Manual fix:** Review untracked files and either `git add` them or add to `.gitignore`.

### 6. Merge Conflicts

- AI can't always resolve merge conflicts during rebase.
- **Manual verification required:** After rebasing, check for conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).

## Pre-PR Checklist (AI Coding Specific)

Before creating your PR, manually verify in your terminal:

```bash
# 1. Confirm you're on the correct branch
git branch

# 2. Confirm all changes are intentional
git status
git diff main...HEAD

# 3. Verify no secrets or temporary files
git diff main...HEAD | grep -i "password\|token\|key\|secret"

# 4. Ensure branch is up to date
git fetch origin
git log HEAD..origin/main --oneline

# 5. Run the tests and linter - AI-generated code may have logical errors
bun run test
bun run check
ruff check . && ruff format --check .
```

## GitHub PR Verification

After creating your PR:

- **Review the Files Changed tab** - ensure no unexpected files are included.
- **Check the diff** - AI may modify files you didn't mean to change.
- **Delete test/temporary branches** created during vibe coding.
- **CI/CD failures** - AI-generated code may pass locally but fail in CI; check the run.

---

## Code Quality and Best Practices

### 7. Hardcoded Values and Magic Numbers

AI often generates hardcoded paths or config. Prefer configurable values:

```python
# BAD - hardcoded
catalog = "dz_demos"

# GOOD - configurable
import os
catalog = os.environ.get("CATALOG", "default_catalog")
```

### 8. Error Handling

AI-generated code may lack error handling. Wrap external calls, catch specific
exceptions (not bare `except:`), and log properly.

### 9. Dependencies and Version Pinning

- Pin dependencies in `pyproject.toml` / `package.json` rather than leaving them unbounded.
- Test with the versions the repo declares before adding new ones.

### 10. Code Documentation

- Add docstrings to public functions explaining purpose, params, and return values.
- Document non-obvious design decisions - but don't add comments that just narrate code.

---

## Repo-Specific Gotchas (Energy Theft Detection)

### 11. Workspace Portability Drift

- This demo must be deployable to **any Databricks workspace**. AI often hard-codes
  workspace IDs, catalog names, or user emails.
- **Always verify:** Search for hardcoded values before committing:
  ```bash
  grep -rE "(adb-[0-9]+|dz_demos|zoccali)" --include="*.py" --include="*.yml" .
  ```

### 12. databricks.yml Target Pollution

- Workspace-specific values (warehouse IDs, Genie space IDs) must go in **target
  overrides**, not the root `variables:` block.
- AI may add values to the wrong section.

### 13. Frontend/Backend Contract Mismatch

- The React frontend (`src/energy_theft_detection/ui/`) and FastAPI backend
  (`src/energy_theft_detection/backend/`) share API contracts.
- If you change a backend endpoint, update the frontend too (and vice versa).
- Run `bun run check` to catch TypeScript type errors from API changes.

### 14. Secrets and Environment Variables

- No hardcoded tokens, API keys, or credentials in code or docs.
- Use a gitignored `.env.local` for local dev (see [`ACCESS_TOKEN_HANDLING.md`](ACCESS_TOKEN_HANDLING.md)).
- For deployed apps, use Databricks Secret Scopes.

### 15. Test Isolation

- Tests must pass without a live Databricks workspace connection.
- The backend has an "offline mode" that returns mock data when `SQL_WAREHOUSE_ID` is unset.
- Don't add tests that require live connectivity unless marked with `@pytest.mark.integration`.

---

## Final Checklist

Before merging AI-generated code:

- [ ] Removed all hardcoded workspace-specific values
- [ ] No secrets or credentials in code
- [ ] Added proper error handling
- [ ] `bun run test` passes
- [ ] `bun run check` passes (TypeScript compiles)
- [ ] `ruff check .` clean
- [ ] Branch is rebased on latest `main`
- [ ] Reviewed the full diff for unintended changes

---

**Remember:** AI is a powerful assistant, but YOU are responsible for the code quality
and Git hygiene. Always review and verify before pushing.
