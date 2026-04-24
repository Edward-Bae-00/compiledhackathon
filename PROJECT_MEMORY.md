# Project Memory

## Last Updated
2026-04-24

## Current State
- Repo now contains a greenfield monorepo for the Fraud Investigator Copilot hackathon MVP.
- `apps/api` is a FastAPI backend with SQLite-backed local persistence, seeded healthcare reference data, deterministic rule scoring, and memo generation.
- `apps/web` is a Next.js app-router frontend with a styled landing page, a four-panel case workspace, and an `Analyze Case` action that prefers the local backend and falls back to a seeded demo case.
- `packages/shared/contracts/case-file.schema.json` holds the current shared case-file contract artifact for frontend/backend alignment.
- `tasks/` now reflects the 2026-04-24 planning state and includes a prioritized product-improvement backlog.

## Durable Decisions
- The MVP is intentionally healthcare-specific, local-first, and single-user.
- Public-data credibility comes from seeded LEIE, NPI, and CMS benchmark slices rather than broad live runtime dependencies.
- Risk scoring is deterministic and rule-backed; memo generation is a formatting layer over those findings.
- The web demo should remain usable even when the backend is unavailable, so seeded fallback behavior is intentional rather than a temporary hack.
- Generated dependencies and build artifacts are intentionally excluded from Git; `node_modules/`, Next.js `.next/`, and Python bytecode caches should be regenerated locally rather than committed.

## Verification Evidence
- Root tests pass with `npm run test`.
- Backend editable install succeeds with `UV_CACHE_DIR=/Users/edward/Desktop/compiled/.uv-cache uv sync --group dev`.
- Production frontend build succeeds with `npm run build:web`.

## Known Risks
- The web intake action currently sends a seeded demo packet to the backend rather than handling arbitrary uploaded files end-to-end.
- Backend storage is intentionally simple and uses a single SQLite connection per app instance; concurrency and production hardening are out of scope for the hackathon.
- Reference datasets are small seeded slices rather than full public datasets, so anomaly detection is illustrative rather than statistically complete.

## Next-Session Notes
- If the next step is product improvement, start with the real intake path for pasted/uploaded evidence, then add citation-grade evidence links and score transparency.
- If the next step is demo polish, add a clean-vs-suspicious case switcher and an API health/fallback indicator.
- If the next step is backend credibility, add optional live NPPES lookup with seeded fallback, more CMS benchmark rows, procedure-specialty mismatch cases, and evidence-link persistence detail.
- If deployment is needed, add environment-driven API base URL docs and a small runbook for starting both apps locally.
