# Task Plan: Fraud Investigator Copilot Hackathon MVP

## Last Updated
2026-04-24

## Goal
Implement a local-first monorepo that ingests a healthcare fraud case packet, extracts provider and claim facts, enriches them with seeded public data and optional NPPES lookup, scores risk deterministically, and presents a 4-panel case workspace with a cited memo draft.

## Current Phase
Phase 8: 2026-04-24 Palantir-First Product Upgrade Implementation

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

### Phase 7: 2026-04-24 Palantir AIP and Live Demo Readiness
- [x] Add optional Palantir AIP backend integration with demo-safe fallback
- [x] Add live-demo intake controls for suspicious, clean, and custom evidence flows
- [x] Verify full test suite and production web build
- **Status:** complete

### Phase 8: 2026-04-24 Palantir-First Product Upgrade Implementation
- [x] Review Claude's product critique against the current implementation
- [x] Verify Palantir API assumptions against official Palantir docs
- [x] Get user approval before implementation
- [x] Implement stage-based Palantir AIP extraction, risk assessment, and memo generation with local fallback
- [x] Add graph-shaped entity/relationship output and render it in the Evidence Graph panel
- [x] Expand deterministic scoring and seeded reference coverage so local demo input remains credible
- [x] Add per-panel Palantir diagnostics, badges, latency, errors, and local-only comparison mode
- [x] Verify backend tests, frontend tests, production web build, and live demo smoke path
- **Status:** complete

## Product Improvement Backlog
| Priority | Improvement | Why It Matters | Suggested First Step |
|----------|-------------|----------------|----------------------|
| P0 | Split Palantir into explicit AIP stages | The current single insight call makes Palantir look bolted on instead of analytically central. | Add `extract_case_facts`, `assess_risk`, and `generate_memo` client methods with per-stage status and fallback behavior. |
| P0 | Use AIP to extract facts from raw narrative evidence | This turns custom intake from CSV-shaped demo input into a realistic investigator workflow. | Send pasted document text to an optional extraction endpoint and merge returned entities, claims, and relationships into the case file. |
| P0 | Render a real entity/relationship graph | Fraud demos are more convincing when they show provider, entity, document, and billing relationships rather than a flat timeline. | Add graph nodes/edges to the API response and render a lightweight network visualization in the Evidence Graph panel. |
| P0 | Real intake path for uploaded or pasted evidence | The current web flow still uses a seeded demo packet, so user-provided evidence is not yet the main product path. | Add a frontend intake form that creates a case, uploads text/CSV documents, then analyzes that actual payload. |
| P0 | Citation-grade evidence links | Investigator trust depends on seeing exactly which document and quote produced each flag. | Persist source document IDs, quote text, and simple location metadata on each risk flag, then render them in the Risk Findings and Memo panels. |
| P1 | Show Palantir output per panel | Judges should see where Palantir contributes, not just a text block at the end. | Add `[AIP]` badges for extracted facts, risk factors, graph edges, and memo provenance. |
| P1 | Palantir diagnostics and local-only toggle | Live demos need transparency when credentials or endpoint latency vary. | Add a collapsible diagnostics panel with configured stages, latency, raw responses, errors, and a local-only comparison control. |
| P1 | Score transparency panel | A single risk score is less credible without a visible rule-by-rule breakdown. | Add score deltas, threshold comparisons, and rule labels to the workspace so users can audit how the score was calculated. |
| P1 | Clean-vs-suspicious demo switcher | A hackathon demo is stronger when it shows the system can avoid over-flagging a normal provider. | Let the user run both seeded demo packets from the UI and compare risk scores/findings. |
| P1 | Optional live NPPES verification with offline fallback | Seeded data keeps demos stable, but live verification increases credibility when network access is available. | Add an environment-gated NPPES lookup path that falls back to `data/reference/npi_registry.json`. |
| P2 | Demo runbook and backend health indicator | The product is easier to judge when setup and API connectivity are obvious. | Add concise local run instructions and show API-connected vs fallback state in the UI header. |
| P2 | Broader seeded benchmark coverage | More procedure and specialty examples make the anomaly scoring feel less toy-like. | Add a few more CMS benchmark rows and tests for specialty/procedure mismatch cases. |

## Recommended Next Actions
1. Implement the stage-based Palantir pipeline first: extraction, risk assessment, and memo generation with strict local fallback.
2. Add the graph-shaped case model and Evidence Graph visualization next, because it makes the investigative workflow visible.
3. Expand deterministic fallback scoring and reference rows in parallel with UI badges, so the demo remains credible when Palantir is not configured.
4. Defer Foundry ontology persistence and webhook/SSE enrichment until tenant-specific ontology, action, and callback details are available.

## Key Questions
1. Should the next implementation assume real Palantir AIP URLs will be supplied, or should it ship with demo-safe mock/fallback responses only?
2. What exact JSON contracts should the AIP Logic functions return for extraction, risk assessment, memo generation, and optional recommended actions?
3. Do we have Foundry ontology API names, object types, action API names, and query API names, or should ontology persistence stay out of scope for this demo iteration?
4. Should file upload/PDF/OCR be included now, or should this phase stay focused on pasted text plus CSV to protect demo timing?
5. What is the target demo path: Palantir-configured live run, local-only fallback run, or an A/B comparison between the two?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Implement in the current directory without a worktree | User explicitly requested all work happen in this directory. |
| Use a monorepo with `apps/web`, `apps/api`, `packages/shared`, `data/reference`, and `data/demo` | Matches the approved blueprint and keeps concerns separated without overengineering. |
| Use SQLite plus local file storage | Fastest reliable persistence for a hackathon MVP. |
| Use seeded LEIE and CMS reference slices with optional live NPPES lookup | Preserves demo reliability while keeping one live credibility path. |
| Keep scoring deterministic and use the LLM layer only for extraction/memo boundaries | Produces a more reliable hackathon demo than model-only risk classification. |
| Make the web `Analyze Case` action prefer the FastAPI backend and fall back to a seeded demo case | Keeps the demo reliable when the API is down while still exercising the real backend path when available. |
| Integrate Palantir AIP as optional enrichment rather than a hard runtime dependency | A live demo should benefit from Palantir when credentials are configured without breaking when endpoint access is unavailable. |
| Keep Palantir credentials in environment variables only | Foundry/AIP bearer tokens must not be committed or exposed in client-side code. |
| Allow local Next.js origins through FastAPI CORS | The live demo runs the frontend and backend on different localhost ports. |
| Make Phase 8 Palantir-first but fallback-safe | A live demo should showcase Palantir where configured while still working if external credentials, tenant functions, or network access fail. |
| Defer Foundry ontology writes until action/query details are provided | Official Palantir APIs apply ontology changes through configured actions, so generic object-create code would be speculative without tenant-specific setup. |

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
