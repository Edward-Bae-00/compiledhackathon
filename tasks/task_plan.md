# Task Plan: Fraud Investigator Copilot Hackathon MVP

## Last Updated
2026-04-24

## Goal
Implement a local-first monorepo that ingests a healthcare fraud case packet, extracts provider and claim facts, enriches them with seeded public data and optional NPPES lookup, scores risk deterministically, and presents a 4-panel case workspace with a cited memo draft.

## Current Phase
Phase 10: 2026-04-24 Live Demo UI/UX Polish

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

### Phase 9: 2026-04-24 YC RFS Requirements Refinement
- [x] Add complaint-ready FCA/qui tam case package builder as the next primary requirement
- [x] Mention citation, corporate-structure, PDF/OCR, legal-elements, and records-request features as future additions
- [x] Refresh the backlog so completed Phase 8 work is no longer presented as the next highest-priority work
- **Status:** complete

### Phase 10: 2026-04-24 Live Demo UI/UX Polish
- [x] Use `ui-ux-pro-max` guidance for a clean healthcare SaaS dashboard direction
- [x] Redesign the first viewport as a live demo command center with visible readiness state
- [x] Add a case summary strip, cleaner investigation panels, and a clean-case empty state
- [x] Replace prototype styling with a responsive executive-workspace visual system
- [x] Verify focused frontend tests, full root tests, and production web build
- **Status:** complete

## Product Improvement Backlog
| Priority | Improvement | Why It Matters | Suggested First Step |
|----------|-------------|----------------|----------------------|
| P0 | Complaint-ready case package builder | This maps the product directly to the YC brief: take an insider tip and package findings into complaint-ready files for FCA/qui tam teams. | Add a package model with theory of liability, allegation-evidence map, exhibit index, damages estimate, open questions, and export sections. |
| P0 | Citation-grade evidence model | Complaint-ready output depends on every allegation being traceable to a document, quote, source location, confidence, and review status. | Extend risk flags and memo inputs with document IDs, quote spans, and reviewed/unreviewed state. |
| P1 | Corporate structure and control tracing | The YC prompt calls out opaque corporate structures, and fraud networks often depend on billing companies, owners, MSOs, shared addresses, and control relationships. | Expand graph entity types and relationship extraction around ownership, management, address, officer, and billing-control links. |
| P1 | Messy PDF/OCR intake | Real law-firm and agency workflows start with PDFs, scans, claim exports, emails, and tables rather than clean pasted text. | Add multi-document PDF upload with extracted text/table previews and preserve source page references. |
| P1 | Legal elements checklist | FCA users need to know whether the record supports false claim, knowledge, materiality, payment, damages, and source credibility. | Add a checklist model and panel that scores each element from linked findings. |
| P2 | Records request and subpoena drafting | Case teams need concrete next steps after triage, especially missing claims, ownership, billing, and communication records. | Generate editable follow-up request drafts from weak evidence areas and graph relationships. |
| P2 | Score transparency panel | A single risk score is less credible without visible rule-by-rule deltas and threshold comparisons. | Add score deltas, benchmark thresholds, and rule labels to the workspace. |
| P2 | Optional live NPPES verification with offline fallback | Seeded data keeps demos stable, but live verification increases credibility when network access is available. | Add an environment-gated NPPES lookup path that falls back to `data/reference/npi_registry.json`. |
| P2 | Broader seeded benchmark coverage | More procedure and specialty examples make anomaly scoring feel less synthetic. | Add more CMS benchmark rows and tests for specialty/procedure mismatch cases. |

## Recommended Next Actions
1. Design the complaint-ready package contract on top of the existing analyzed case response.
2. Implement citation-grade evidence links before package export, because the package builder depends on source-linked proof.
3. Add a workspace panel or export preview for theory of liability, allegation-evidence map, exhibits, damages estimate, open questions, and follow-up requests.
4. Keep PDF/OCR, corporate-control enrichment, legal-elements scoring, and subpoena drafting as follow-on slices after the package builder has a working demo path.

## Key Questions
1. Should the first package export be a Markdown/HTML preview, downloadable PDF/DOCX, or both?
2. Which liability theories should be supported first: excluded-provider billing, upcoding, medically unnecessary billing, kickbacks, false certification, or billing-company control?
3. Should the package include attorney-review workflow states now, or stay single-user and demo-focused?
4. Should damages estimates use simple seeded assumptions, user-entered claim totals, or a live claims export?
5. Should records-request drafting ship with the package builder or remain a separate follow-on feature?

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
| Keep Phase 10 as frontend-only polish | The user asked for a cleaner live-demo UI, so API contracts, scoring, Palantir behavior, and package-builder requirements stayed unchanged. |
| Use a healthcare-trust executive workspace direction | `ui-ux-pro-max` recommended a clean healthcare SaaS palette, flat accessible styling, strong hierarchy, and responsive dashboard scanability. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `uv` cache path under the sandboxed home directory was not writable | 1 | Redirected `UV_CACHE_DIR` to a repo-local cache directory. |
| Python dependency sync failed because `apps/api/README.md` was missing | 1 | Added the missing README so the package metadata could resolve. |
| `uv run pytest` tried to build the unfinished local package during the red phase | 1 | Switched red/green test runs to `.venv/bin/pytest -q` until packaging was configured. |
| Vitest compiled JSX in classic mode and threw `React is not defined` | 1 | Enabled the automatic JSX transform in `apps/web/vitest.config.ts`. |
| Final `uv sync` needed network to fetch the `hatchling` build backend | 1 | Re-ran the sync with network permission and verified the editable install. |
| Phase 10 production build warned about `align-items: start` mixed support | 1 | Replaced `start` alignment values with `flex-start` and reran the production build cleanly. |

## Notes
- Follow the approved blueprint unless local implementation constraints force a narrower interpretation.
- TDD applies: tests before production code for each new behavior slice.
- Keep changes scoped to the MVP; skip auth, OCR, queues, and enterprise concerns.
