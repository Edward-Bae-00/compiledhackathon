# Task Plan: Fraud Investigator Copilot Hackathon MVP

## Last Updated
2026-04-24

## Goal
Implement a local-first monorepo that ingests a healthcare fraud case packet, extracts provider and claim facts, enriches them with seeded public data and optional NPPES lookup, scores risk deterministically, and presents a 4-panel case workspace with a cited memo draft.

## Current Phase
Phase 6: 2026-04-24 Product Improvement Planning

## Phases
### Phase 1: Repo Setup and Baseline
- [x] Confirm workspace state and local toolchain
- [x] Record the approved product scope and constraints
- [x] Scaffold monorepo layout and baseline test harnesses
- **Status:** complete

### Phase 2: Backend Foundations
- [x] Define shared API/data contracts
- [x] Implement case/document storage, ingestion, extraction, enrichment, and scoring flows
- [x] Seed demo/reference datasets and backend tests
- **Status:** complete

### Phase 3: Frontend Workspace
- [x] Implement case intake and analysis flow
- [x] Implement evidence, findings, and memo panels
- [x] Add frontend tests for the core workspace behavior
- **Status:** complete

### Phase 4: Integration and Verification
- [x] Verify end-to-end behavior with backend and frontend test commands
- [x] Run review-quality checks and record results
- [x] Fix issues discovered during verification
- **Status:** complete

### Phase 5: Delivery
- [x] Summarize changes and known gaps
- [x] Update durable project memory if applicable
- [x] Hand off with verification evidence
- **Status:** complete

### Phase 6: 2026-04-24 Product Improvement Planning
- [x] Normalize task-folder dates to today's date
- [x] Review current product surface for high-leverage improvements
- [x] Add a prioritized refinement backlog
- **Status:** complete

## Product Improvement Backlog
| Priority | Improvement | Why It Matters | Suggested First Step |
|----------|-------------|----------------|----------------------|
| P0 | Real intake path for uploaded or pasted evidence | The current web flow still uses a seeded demo packet, so user-provided evidence is not yet the main product path. | Add a frontend intake form that creates a case, uploads text/CSV documents, then analyzes that actual payload. |
| P0 | Citation-grade evidence links | Investigator trust depends on seeing exactly which document and quote produced each flag. | Persist source document IDs, quote text, and simple location metadata on each risk flag, then render them in the Risk Findings and Memo panels. |
| P1 | Score transparency panel | A single risk score is less credible without a visible rule-by-rule breakdown. | Add score deltas, threshold comparisons, and rule labels to the workspace so users can audit how the score was calculated. |
| P1 | Clean-vs-suspicious demo switcher | A hackathon demo is stronger when it shows the system can avoid over-flagging a normal provider. | Let the user run both seeded demo packets from the UI and compare risk scores/findings. |
| P1 | Optional live NPPES verification with offline fallback | Seeded data keeps demos stable, but live verification increases credibility when network access is available. | Add an environment-gated NPPES lookup path that falls back to `data/reference/npi_registry.json`. |
| P2 | Demo runbook and backend health indicator | The product is easier to judge when setup and API connectivity are obvious. | Add concise local run instructions and show API-connected vs fallback state in the UI header. |
| P2 | Broader seeded benchmark coverage | More procedure and specialty examples make the anomaly scoring feel less toy-like. | Add a few more CMS benchmark rows and tests for specialty/procedure mismatch cases. |

## Recommended Next Actions
1. Build the real evidence intake path first, because it changes the product from a demo button into a usable workflow.
2. Add citation-grade evidence links next, because they make every finding and memo claim easier to trust.
3. Add score transparency after citations, because the backend already calculates rule deltas and the UI can expose them without changing the scoring model.

## Key Questions
1. How do we keep the MVP credible without runtime dependence on multiple live public APIs?
2. What is the smallest extraction/enrichment model that still produces a convincing case file?
3. How do we keep the UI demo-ready while staying within an empty greenfield repo?
4. Should the next product iteration prioritize real user intake, richer investigative credibility, or demo presentation polish?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Implement in the current directory without a worktree | User explicitly requested all work happen in this directory. |
| Use a monorepo with `apps/web`, `apps/api`, `packages/shared`, `data/reference`, and `data/demo` | Matches the approved blueprint and keeps concerns separated without overengineering. |
| Use SQLite plus local file storage | Fastest reliable persistence for a hackathon MVP. |
| Use seeded LEIE and CMS reference slices with optional live NPPES lookup | Preserves demo reliability while keeping one live credibility path. |
| Keep scoring deterministic and use the LLM layer only for extraction/memo boundaries | Produces a more reliable hackathon demo than model-only risk classification. |
| Make the web `Analyze Case` action prefer the FastAPI backend and fall back to a seeded demo case | Keeps the demo reliable when the API is down while still exercising the real backend path when available. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `uv` cache path under the sandboxed home directory was not writable | 1 | Redirected `UV_CACHE_DIR` to a repo-local cache directory. |
| Python dependency sync failed because `apps/api/README.md` was missing | 1 | Added the missing README so the package metadata could resolve. |
| `uv run pytest` tried to build the unfinished local package during the red phase | 1 | Switched red/green test runs to `.venv/bin/pytest -q` until packaging was configured. |
| Vitest compiled JSX in classic mode and threw `React is not defined` | 1 | Enabled the automatic JSX transform in `apps/web/vitest.config.ts`. |
| Final `uv sync` needed network to fetch the `hatchling` build backend | 1 | Re-ran the sync with network permission and verified the editable install. |

## Notes
- Follow the approved blueprint unless local implementation constraints force a narrower interpretation.
- TDD applies: tests before production code for each new behavior slice.
- Keep changes scoped to the MVP; skip auth, OCR, queues, and enterprise concerns.
