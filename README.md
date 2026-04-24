# Fraud Investigator Copilot

Local-first healthcare fraud triage demo with a Next.js workspace, FastAPI backend, seeded public-data references, deterministic risk scoring, and optional Palantir AIP enrichment.

## Local Demo

Install dependencies:

```bash
npm install
cd apps/api && uv sync --group dev
```

Start the backend in one terminal:

```bash
npm run dev:api
```

Start the frontend in another terminal:

```bash
npm run dev:web
```

Open the Next.js URL, usually `http://localhost:3000`. The live demo can run in three modes:

- `Suspicious Preset`: shows LEIE exclusion and abnormal billing findings.
- `Clean Preset`: shows a low-risk control case.
- `Custom Intake`: lets you paste a title, tip, document name, document type, and CSV/text content.

The UI status strip shows whether the browser is using the FastAPI backend or the local fallback packet, whether Palantir AIP returned staged enrichment, and which case source is active. Enable `Local-only` in the strip to force an A/B comparison run without Palantir calls.

## Optional Palantir AIP

For the strongest demo, create three AIP Logic functions in Palantir and copy each runnable request URL from the function's Uses tab. The app calls them server-side with the same bearer token:

- `extract_case_facts`: accepts raw case and document text; returns `entities`, `claims`, and `relationships`.
- `assess_risk`: accepts the structured case file and graph; returns `risk_factors`.
- `generate_memo`: accepts the final case file; returns `memo_markdown` and optional `recommendation`.

Configure the backend environment before starting `npm run dev:api`:

```bash
export PALANTIR_AIP_EXTRACT_FACTS_URL="https://<your-foundry-host>/<extract-function-run-endpoint>"
export PALANTIR_AIP_ASSESS_RISK_URL="https://<your-foundry-host>/<risk-function-run-endpoint>"
export PALANTIR_AIP_GENERATE_MEMO_URL="https://<your-foundry-host>/<memo-function-run-endpoint>"
export PALANTIR_API_TOKEN="<your-token>"
export PALANTIR_HOSTNAME="<your-foundry-host>" # optional status check
```

Legacy single-call mode is still supported with `PALANTIR_AIP_LOGIC_URL`, but the staged variables make Palantir visible in the intake, graph, findings, memo, and diagnostics panels.

Do not commit tokens. If these variables are missing, `PALANTIR_FORCE_LOCAL=true`, the UI `Local-only` toggle is enabled, or any request fails, the app returns clearly labeled local fallback findings so the live demo remains usable.

## Verification

```bash
npm run test
npm run build:web
```
