# Findings & Decisions

## Current Review Date
2026-04-24

## Requirements
- Build a healthcare-focused Fraud Investigator Copilot hackathon MVP.
- Use a monorepo with a Next.js frontend and FastAPI backend.
- Support upload/paste intake, evidence extraction, LEIE/NPPES/CMS enrichment, deterministic risk scoring, and memo generation.
- Use local-first storage with seeded public data and one synthetic demo case.
- Implement in the current working directory rather than a git worktree.

## Research Findings
- The repo started as an empty Git repository with no tracked files and no existing conventions beyond `AGENTS.md`.
- The local toolchain is present: Node.js `v25.9.0`, npm `11.12.1`, Python `3.14.4`, and `uv 0.11.6`.
- The repository has a GitHub remote, so `PROJECT_MEMORY.md` is relevant after meaningful implementation work.
- The backend can be verified entirely with local seeded datasets; only the final editable install path required network access for the `hatchling` build backend.
- The web app can stay demo-stable by preferring live local API analysis and falling back to a seeded case file when the backend is unavailable.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Start with backend and frontend scaffolds plus tests before feature code | Reduces integration drift in an empty repo and satisfies the TDD requirement. |
| Store shared contracts as JSON schema-style fixtures and TypeScript/Python typed models rather than code generation | Keeps setup simpler in a greenfield hackathon repo. |
| Use one seeded suspicious demo packet and one lighter clean control packet | Supports both the demo and risk-ranking verification. |
| Keep backend persistence to a single SQLite connection per app instance | Simplifies local development and allows in-memory storage during pytest runs. |
| Model the frontend around a single `WorkspaceCaseData` object | Keeps the 4-panel UI simple and matches the backend analyze payload closely. |

## 2026-04-24 Product Improvement Findings
- The highest-impact product gap is intake: the web `Analyze Case` button prefers the backend but still sends a hard-coded seeded packet rather than user-entered or uploaded evidence.
- Evidence credibility should improve before adding more scoring complexity. Risk findings currently include evidence quote strings, but not enough source linkage for an investigator to jump from a flag to the exact document context.
- Score transparency is a strong next UI improvement because the backend already stores `score_delta`, `severity`, `reason_code`, and benchmark context for each flag.
- The demo would be more persuasive with a clean-vs-suspicious case switcher so judges can see both positive detection and low-risk restraint.
- Live NPPES lookup should be optional and environment-gated so the product keeps its local-first demo reliability.
- Broader seeded reference data would make the MVP feel less synthetic, especially if it adds more procedure codes, specialties, and mismatch examples.

## 2026-04-24 Palantir AIP Findings
- The codebase did not include Palantir before this iteration.
- The best first integration is an optional backend Palantir AIP Logic connector using server-side environment variables, because tenant-specific OSDK packages require Developer Console setup and should not block the demo.
- The backend should send analyzed case-file JSON to Palantir AIP and render the returned recommendation as a supplemental triage insight, not as the source of deterministic risk scoring.
- The frontend must keep a local fallback path so missing Palantir credentials, endpoint errors, or API downtime do not break the live walkthrough.
- FastAPI needs CORS for localhost Next.js origins because the live demo runs browser and API servers on different ports.
- Node.js `v25.9.0` exposes experimental Web Storage by default in this environment and creates a broken server-side `localStorage` object; disabling web storage for `next dev` prevents `localStorage.getItem is not a function` 500s.

## 2026-04-24 Claude Palantir Review Findings
- I agree with Claude's core product critique: Palantir is currently a single optional insight call, extraction is CSV/substr based, scoring has only a few deterministic rules, the "Evidence Graph" is a timeline, and memo generation is templated.
- The highest-value next implementation is not more UI polish by itself; it is a stage-based case-analysis pipeline where Palantir AIP can extract raw facts, assess risk, and draft the memo through separate contracts.
- The fastest credible demo path is three optional AIP stages: `extract_case_facts`, `assess_risk`, and `generate_memo`. `recommended_actions` can be folded into memo output or added as a fourth optional stage if time allows.
- Foundry ontology persistence is valuable but should not be the immediate dependency unless tenant-specific object types, action API names, query API names, and permissions are available.
- Official Palantir docs show AIP Logic functions can be run externally from the Uses tab when they do not return ontology edits, while ontology edits should be applied through actions or automations.
- Official Palantir Ontologies v2 docs show action application uses `POST /api/v2/ontologies/{ontology}/actions/{action}/apply`, query execution uses `POST /api/v2/ontologies/{ontology}/queries/{queryApiName}/execute`, and object reads use `GET /api/v2/ontologies/{ontology}/objects/{objectType}`.
- Claude's generic "POST objects to create case objects" framing needs correction: durable ontology writes should go through configured actions rather than speculative generic object-create endpoints.
- Webhooks/SSE would be realistic for long-running enrichment, but they add demo fragility; the next phase should use synchronous short-timeout stages with visible fallback first.
- Local scoring still matters even with Palantir because it protects the demo from zero-score unknown inputs and makes an A/B comparison meaningful.

## 2026-04-24 Phase 8 Implementation Findings
- Palantir is now stage-based in the backend: extraction, risk assessment, and memo generation have separate URLs, stage statuses, latency, raw responses, and fallback modes.
- The legacy `PALANTIR_AIP_LOGIC_URL` single recommendation path remains supported for backward compatibility.
- `/cases/{case_id}/analyze?force_local=true` forces local-only mode for A/B demo comparison without calling configured Palantir endpoints.
- Narrative text extraction now recognizes provider/NPI/procedure/amount/patient-count patterns and billing-management relationships, so custom pasted text can score without CSV.
- Local scoring now includes unknown NPI, high claim volume, and suspicious relationship language in addition to exclusion, CMS benchmark, and specialty/procedure mismatch rules.
- The API response now includes `evidence_graph` nodes/edges, risk/memo provenance, and a `palantir` diagnostics object.
- The frontend now renders entity graph nodes/edges, `[AIP]` versus local badges, memo source, Palantir diagnostics, raw response details, and a local-only toggle.
- Seeded LEIE, NPI, and CMS benchmark reference files now include broader rows for billing companies, DME, lab testing, and additional procedures.

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Worktree isolation conflicted with the user's request to work directly in the repo root | Followed the explicit user instruction and documented the override in `task_plan.md`. |
| `uv sync` initially failed because the backend package had no discoverable wheel contents | Added a Hatch wheel package declaration for `src/fraudcopilot`. |
| `uv sync` and `uv run pytest` have different needs during the red phase | Used `--no-install-project` and direct `.venv` invocations until the package layout existed. |
| API venv console scripts point at an older absolute path after the repo move | Run API tests through `.venv/bin/python -m pytest` instead of the stale `.venv/bin/pytest` launcher. |
| `npm run dev:api` could not import `fraudcopilot` without package install/PYTHONPATH | Pass `--app-dir src` to Uvicorn in the root dev script. |
| `next dev` returned 500 under Node 25 due broken server-side `localStorage` | Set `NODE_OPTIONS=--no-webstorage` in the frontend dev script. |

## Resources
- Local instructions: `/Users/edward/Desktop/compiled/AGENTS.md`
- Planning skill templates: `/Users/edward/.agents/skills/planning-with-files/templates/`
- Shared contract artifact: `packages/shared/contracts/case-file.schema.json`
- Demo reference data: `data/reference/*.json`, `data/demo/*.json`
- Palantir AIP Logic getting started: `https://www.palantir.com/docs/foundry/logic/getting-started`
- Palantir Ontologies v2 apply action API: `https://www.palantir.com/docs/foundry/api/v2/ontologies-v2-resources/actions/apply-action`
- Palantir Ontologies v2 execute query API: `https://www.palantir.com/docs/foundry/api/v2/ontologies-v2-resources/queries/execute-query`
- Palantir Ontologies v2 list objects API: `https://www.palantir.com/docs/foundry/api/ontologies-v2-resources/ontology-objects/list-objects`

## Visual/Browser Findings
- None.
