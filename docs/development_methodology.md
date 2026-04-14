# Development Methodology: Plan/Agent TDD with AI Pair Programming

A reusable guide for building Databricks Apps using the iterative Plan Mode / Agent
Mode workflow with test-driven development. Adapted from the ENSEK Ignition Lakebase
Demo methodology for stateless APX applications.

---

## Overview

This methodology combines three practices:

1. **Plan Mode** — collaborative design and decision-making before any code is written
2. **Agent Mode** — autonomous code execution against an approved plan
3. **Test-Driven Development (TDD)** — acceptance tests written first, defining
   expected behaviour before implementation

The result is a tight feedback loop: you decide *what* the system should do (Plan),
define *how to verify it* (Tests), then build *just enough code* to make the tests
pass (Agent).

---

## Phase 0: Project Setup & PRD

### Goal
Establish the project scaffold, data layer, documentation, and a living PRD before
writing any application logic.

### Steps

1. **Start in Plan Mode.** Describe the business problem, target customer, and demo
   objectives. The AI asks clarifying questions to scope the work.

2. **Create the PRD collaboratively.** Walk through functional requirements. For each
   feature:
   - Define the persona it serves (who opens this page?)
   - Identify the data entities and queries involved
   - Specify the workflow steps
   - Decide: Tier 1, Tier 2, or backlogged?

3. **Create supporting docs before code:**
   - `docs/tech_stack.md` — technology choices with rationale
   - `docs/backlog.md` — out-of-scope features, prioritised
   - `docs/claude_prompts.md` — log every prompt for traceability
   - `docs/issues_and_fixes.md` — living log of errors encountered
   - `docs/databricks_workspace_setup.md` — UC, Genie, AI Gateway setup
   - `docs/demo_architecture.md` — architecture overview and demo walkthrough

4. **Scaffold the project.** Switch to Agent Mode to:
   - Create the APX directory structure
   - Set up CSS/theming (branding)
   - Define Pydantic response models (no ORM for stateless apps)
   - Create skeleton API routes with `response_model` and `operation_id`
   - Create skeleton frontend routes with placeholder content

5. **Hydrate test data.** Create scripts that generate synthetic data, write to Delta
   tables in Unity Catalog, register ML models in MLflow, and create Genie Spaces.

### Artifacts produced
```
docs/
  PRD.md                           # Living PRD
  tech_stack.md                    # Technology decisions
  backlog.md                       # Deferred features
  claude_prompts.md                # Prompt log
  issues_and_fixes.md              # Error log
  databricks_workspace_setup.md    # Workspace configuration
  demo_architecture.md             # Architecture overview
scripts/
  generate_synthetic_data.py       # Data generation
  setup_unity_catalog.py           # UC tables, metric views
  register_models.py               # MLflow model registration
  create_genie_space.py            # Genie Space setup
src/
  <app>/backend/routes/            # API skeletons
  <app>/backend/models/            # Pydantic response models
  <app>/ui/routes/                 # Frontend skeletons
```

---

## Phase 1: Test-Driven Acceptance Criteria

### Goal
Define what "done" looks like *before* writing implementation code.

### Steps

1. **Switch to Plan Mode.** Propose acceptance test cases for the PRD's functional
   requirements. Think like a product owner:
   - "If I open the dashboard, the KPI tiles show non-zero values from Delta"
   - "If I ask Genie a question, I get a SQL-backed answer within 30 seconds"
   - "If I click a HIGH risk account, the LLM summary loads within 10 seconds"

2. **Review the proposed test matrix.** Test cases organised by feature:
   - Each case has: ID, priority (MUST/SHOULD/NICE), steps, expected result
   - Identify cases that will initially fail (that's the point)
   - Approve or refine

3. **Switch to Agent Mode.** Create:
   - Acceptance test section in the PRD
   - `tests/conftest.py` with shared fixtures
   - `tests/test_dashboard.py` — Susie's executive dashboard
   - `tests/test_investigation.py` — Robbie's workbench
   - `tests/test_governance.py` — AI governance page
   - `tests/test_genie.py` — Genie Conversation API proxy
   - `tests/test_llm.py` — Bedrock LLM case summary

4. **Run the tests.** Most will fail — that's expected and intentional.

---

## Phase 2: Implementation (Make Tests Pass)

### Goal
Implement backend and frontend code to make failing tests pass, one feature at a time.

### Steps

1. **Run the test suite.** Identify which tests fail and group by root cause:
   ```bash
   uv run pytest tests/ -v --tb=short
   ```

2. **Pick one failing group.** E.g., "dashboard KPI tiles return 422".

3. **Switch to Plan Mode** (optional for complex changes). Discuss the approach:
   - Where does the code change?
   - What's the minimal change to make the tests pass?
   - Side effects?

4. **Switch to Agent Mode.** Make the code change and re-run affected tests.

5. **Repeat** until all MUST-priority tests pass.

6. **Verify in the browser:**
   ```bash
   uv run apx dev start
   ```

### Key principle
> Never write code that isn't motivated by a failing test.

---

## Phase 3: Frontend Wiring

### Goal
Connect the React frontend to the validated backend API.

### Steps

1. OpenAPI client auto-regenerates when dev servers are running.

2. Replace placeholder content in frontend routes with real API calls:
   - Use `useXSuspense` hooks with `Suspense` boundaries
   - Use `selector()` for clean data destructuring
   - Wrap data-fetching components in `ErrorBoundary`

3. Add shadcn/ui components as needed:
   ```bash
   uv run apx components add <component> --yes
   ```

4. Verify each page in the browser after wiring.

---

## Phase 4: Polish & Demo Prep

### Goal
Final validation, presentation content, deploy, and rehearsal.

### Steps

1. Run full test suite:
   ```bash
   uv run pytest tests/ -v
   ```

2. Fill in the Presentation page content (Show-Me-Don't-Tell-Me).

3. Review `docs/issues_and_fixes.md` for unresolved items.

4. Deploy:
   ```bash
   uv run apx build
   databricks bundle deploy --profile azure-field-demos
   ```

---

## The Plan/Agent Loop (Quick Reference)

```
┌─────────────────────────────────────────────────┐
│                  PLAN MODE                       │
│  - Discuss requirements and trade-offs           │
│  - AI asks structured clarifying questions       │
│  - Agree on approach before any code changes     │
│  - Review proposed test cases / architecture     │
└──────────────────────┬──────────────────────────┘
                       │ "approved. proceed."
                       ▼
┌─────────────────────────────────────────────────┐
│                  AGENT MODE                      │
│  - AI executes the approved plan                 │
│  - Creates/edits files, runs commands            │
│  - Documents errors in docs/issues_and_fixes.md  │
│  - Logs prompts in docs/claude_prompts.md        │
└──────────────────────┬──────────────────────────┘
                       │ Hit an ambiguity or error?
                       ▼
              Back to PLAN MODE
```
