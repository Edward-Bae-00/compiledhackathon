# Project Memory

## Last Updated
2026-04-24

## Current State
- Repo now contains a greenfield monorepo for the Fraud Investigator Copilot hackathon MVP.
- `apps/api` is a FastAPI backend with SQLite-backed local persistence, seeded healthcare reference data, deterministic rule scoring, memo generation, local-demo CORS, and optional Palantir AIP Logic enrichment.
- `apps/api` now supports staged Palantir AIP Logic enrichment for extraction, risk assessment, and memo generation, plus legacy single-insight mode and `force_local` analysis mode.
- `apps/web` is a Next.js app-router frontend with a demo-ready intake console, suspicious/clean/custom case modes, a local-only toggle, graph/finding/memo Palantir badges, diagnostics, and fallback behavior when the local backend is unavailable.
- `packages/shared/contracts/case-file.schema.json` holds the current shared case-file contract artifact, including graph and Palantir diagnostics response fields.
- `tasks/` now reflects the 2026-04-24 planning state and includes a prioritized product-improvement backlog.
- `.codex/skills/ui-ux-pro-max/` was installed with `uipro init --ai codex` for Codex UI/UX Pro Max guidance.

## Durable Decisions
- The MVP is intentionally healthcare-specific, local-first, and single-user.
- Public-data credibility comes from seeded LEIE, NPI, and CMS benchmark slices rather than broad live runtime dependencies.
- Risk scoring is deterministic and rule-backed; memo generation is a formatting layer over those findings.
- The web demo should remain usable even when the backend is unavailable, so seeded fallback behavior is intentional rather than a temporary hack.
- Generated dependencies and build artifacts are intentionally excluded from Git; `node_modules/`, Next.js `.next/`, and Python bytecode caches should be regenerated locally rather than committed.
- Palantir AIP is a server-side optional enrichment layer configured through `PALANTIR_AIP_LOGIC_URL`, `PALANTIR_API_TOKEN`, and optional `PALANTIR_HOSTNAME`; tokens must never be committed or exposed to the frontend.
- The next Palantir upgrade should be stage-based and fallback-safe: extraction, risk assessment, and memo generation should be optional server-side AIP calls with local deterministic behavior preserved.
- Foundry ontology persistence should be deferred until the tenant's ontology API names, action API names, query API names, and permissions are known.
- Local-only comparison is available with `POST /cases/{case_id}/analyze?force_local=true` and the frontend `Local-only` toggle.
- `README.md` now documents the live demo runbook, staged Palantir AIP environment variables, function request/response contracts, diagnostics fields, and Foundry ontology follow-up guidance.

## Verification Evidence
- Root tests pass with `npm run test`.
- Backend editable install succeeds with `UV_CACHE_DIR=/Users/edward/Desktop/compiled/.uv-cache uv sync --group dev`.
- Production frontend build succeeds with `npm run build:web`.
- Focused Palantir/API tests pass with `cd apps/api && .venv/bin/python -m pytest -q tests/test_api_flow.py`.
- Focused live-demo frontend tests pass with `npm run test --workspace apps/web -- src/__tests__/workspace-shell.test.tsx`.
- After Palantir/live-demo work, root `npm run test` reports web `6 passed` and API `5 passed`; `npm run build:web` completes successfully.
- After Phase 8 work, root `npm run test` reports web `7 passed` and API `8 passed`; `npm run build:web` completes successfully.
- JSON validation for the shared schema and seeded reference data reports `json ok`.
- Live smoke on 2026-04-24: backend `GET /health` returned `{"status":"ok"}` and frontend `GET /` returned HTTP `200`.
- `rtk uipro init --ai codex` completed successfully after sandbox escalation; it generated `.codex/skills/ui-ux-pro-max/`.

## Known Risks
- Custom intake currently supports pasted text/CSV content in a single document field; multi-file upload and OCR are still out of scope.
- Palantir live mode requires the user to create an AIP Logic function and provide a runnable endpoint/token via environment variables.
- Existing virtualenv console scripts had stale absolute shebangs after the repo move, so root scripts intentionally use `.venv/bin/python -m pytest` and `.venv/bin/python -m uvicorn`.
- `next dev` under Node.js `v25.9.0` needs `NODE_OPTIONS=--no-webstorage` in this environment to avoid a broken server-side `localStorage` global.
- Backend storage is intentionally simple and uses a single SQLite connection per app instance; concurrency and production hardening are out of scope for the hackathon.
- Reference datasets are small seeded slices rather than full public datasets, so anomaly detection is illustrative rather than statistically complete.
- Palantir live mode still requires the user to create tenant-specific AIP Logic functions matching the documented contracts and provide endpoint URLs/tokens through environment variables.
- Foundry ontology persistence and async webhook/SSE enrichment remain intentionally deferred.

## Next-Session Notes
- If the next step is product improvement, add multi-document upload, citation-grade evidence links with source offsets, and score transparency.
- If the next step is demo polish, run through the README live-demo script with the actual Palantir AIP endpoint configured.
- If the next step is backend credibility, add optional live NPPES lookup with seeded fallback, more CMS benchmark rows, procedure-specialty mismatch cases, and evidence-link persistence detail.
- If deployment is needed, add environment-driven API base URL docs and a small runbook for starting both apps locally.
