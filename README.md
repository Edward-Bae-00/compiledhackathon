# Fraud Investigator Copilot

Local-first healthcare fraud triage demo with a Next.js workspace, FastAPI backend, seeded public-data references, deterministic risk scoring, evidence graph output, and optional staged Palantir AIP enrichment.

## What the Demo Shows

- Intake of a healthcare fraud tip plus claim or narrative evidence.
- Local extraction and deterministic risk scoring with seeded LEIE, NPPES, and CMS benchmark data.
- Optional Palantir AIP stages for document extraction, risk assessment, and memo generation.
- Entity relationship graph connecting providers, procedures, documents, reference matches, and billing entities.
- A memo panel with local or AIP provenance plus Palantir diagnostics for configured stages.

## Next Requirement: Complaint-Ready Case Packages

The next product requirement is a complaint-ready package builder for False Claims Act and qui tam case development. This is planned work, not part of the current runtime demo.

The package builder should turn an analyzed case file into a structured packet a whistleblower law firm, state attorney general, or inspector general team can review quickly:

- **FCA theory of liability:** classify the likely theory, such as excluded-provider billing, upcoding, medically unnecessary billing, kickbacks, false certification, or billing-company control.
- **Evidence-to-allegation map:** connect each proposed allegation to source documents, quote text, source location, confidence, and review status.
- **Exhibit index:** group documents, claims, graph relationships, public-data matches, and supporting quotes into complaint-ready exhibits.
- **Damages and exposure estimate:** summarize suspicious billing volume, rough lookback period, affected programs, claim amount, and recovery/penalty assumptions.
- **Draft export packet:** generate a package containing the investigator memo, chronology, entity graph, exhibit index, open questions, and recommended follow-up records requests.

Success criteria: after reviewing the package, a fraud investigator or FCA lawyer can see what is alleged, which evidence supports it, which elements are still weak, and what records should be requested next.

## Additional Future Requirements

- **Citation-grade evidence model:** store document IDs, page/line/span locations, extracted quote text, confidence, and human review status for every finding.
- **Corporate structure and control tracing:** expand the graph to include owners, billing companies, management services organizations, shared addresses, officers, and control relationships.
- **Messy PDF/OCR intake:** accept multi-document PDF bundles, OCR text, and extracted tables instead of relying only on pasted text or CSV content.
- **Legal elements checklist:** score readiness against FCA elements such as false claim, knowledge, materiality, government payment, damages, and source credibility.
- **Records request and subpoena drafting:** generate next-step requests for claims data, ownership records, billing-company communications, and preservation letters.

## Run Everything

Prerequisites:

- Node.js and npm.
- Python with `uv`.
- Optional: Palantir Foundry/AIP access and a bearer token.

Install dependencies once from the repo root:

```bash
npm install
cd apps/api && uv sync --group dev
cd ../..
```

### Run without Palantir

Terminal 1:

```bash
npm run dev:api
```

Terminal 2:

```bash
npm run dev:web
```

Open:

```text
http://localhost:3000
```

Confirm the backend is running:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### Run with Palantir

Create a local secrets file. This path is ignored by Git:

```bash
mkdir -p apps/api/.secrets
touch apps/api/.secrets/palantir.env
```

Add your Palantir values to `apps/api/.secrets/palantir.env`:

```bash
export PALANTIR_HOSTNAME="your-foundry-hostname.palantirfoundry.com"
export PALANTIR_API_TOKEN="your-palantir-api-token"
export PALANTIR_AIP_EXTRACT_FACTS_URL="https://<your-foundry-host>/<extract-function-run-endpoint>"
export PALANTIR_AIP_ASSESS_RISK_URL="https://<your-foundry-host>/<risk-function-run-endpoint>"
export PALANTIR_AIP_GENERATE_MEMO_URL="https://<your-foundry-host>/<memo-function-run-endpoint>"
```

Start the backend with those values loaded:

```bash
source apps/api/.secrets/palantir.env
npm run dev:api
```

Start the frontend in another terminal:

```bash
npm run dev:web
```

Check whether the backend can reach Palantir:

```bash
curl http://127.0.0.1:8000/integrations/palantir/status
```

A healthy result should look like:

```json
{"configured":true,"reachable":true,"mode":"live"}
```

Then open `http://localhost:3000` and click `Analyze Case`. The UI status strip should show the FastAPI backend as connected and Palantir mode as `live`, `partial`, `configured`, or an error state.

### How to find Palantir values

- `PALANTIR_HOSTNAME`: open Foundry in your browser and copy the domain after `https://` and before the next `/`. Example: `my-company.palantirfoundry.com`.
- `PALANTIR_API_TOKEN`: in Foundry, go to `Account` -> `Settings` -> `Tokens` -> `Create token`, then copy the generated token immediately.
- `PALANTIR_AIP_*_URL`: create the three AIP Logic functions, then copy each runnable request URL from the function's Uses tab.

Keep Palantir secrets only in `apps/api/.secrets/palantir.env` or in your backend host's secret manager. Do not put them in `apps/web`, do not prefix them with `NEXT_PUBLIC_`, and do not commit real tokens or `.env` files.

Demo flow:

1. Select `Suspicious Preset` and click `Analyze Case`.
2. Show the risk score, LEIE/CMS findings, graph nodes and edges, memo, and Palantir diagnostics.
3. Select `Clean Preset` and run again to show low-risk restraint.
4. Select `Custom Intake`, paste narrative evidence or CSV content, and run the API-backed analysis.
5. Enable `Local-only` in the status strip to force an A/B run without Palantir calls.

The app remains demo-safe if the backend or Palantir is unavailable. The frontend falls back to seeded packets if the local API cannot be reached, and the backend falls back to local extraction/scoring/memo output if Palantir is not configured or fails.

## Palantir Integration Overview

The Palantir integration is implemented server-side in:

```text
apps/api/src/fraudcopilot/app.py
```

Main integration points:

- `PalantirAipClient.from_env()` reads environment variables.
- `extract_case_facts()` calls the extraction AIP Logic function.
- `assess_risk()` calls the risk assessment AIP Logic function.
- `generate_memo()` calls the memo generation AIP Logic function.
- `/cases/{case_id}/analyze` orchestrates local extraction, optional AIP extraction, local scoring, optional AIP risk factors, graph building, optional AIP memo generation, and diagnostics.

The frontend consumes the returned `palantir`, `palantir_insight`, `risk_flags.source`, `memo.source`, and `evidence_graph` fields to show visible AIP contributions in each panel.

Official Palantir references:

- AIP Logic getting started: https://www.palantir.com/docs/foundry/logic/getting-started
- Ontologies v2 apply action API: https://www.palantir.com/docs/foundry/api/v2/ontologies-v2-resources/actions/apply-action
- Ontologies v2 execute query API: https://www.palantir.com/docs/foundry/api/v2/ontologies-v2-resources/queries/execute-query

## Configure Palantir AIP

Create three AIP Logic functions in Palantir. Copy each function's runnable request URL from its Uses tab and store the URLs in `apps/api/.secrets/palantir.env` before starting the FastAPI backend.

```bash
export PALANTIR_AIP_EXTRACT_FACTS_URL="https://<your-foundry-host>/<extract-function-run-endpoint>"
export PALANTIR_AIP_ASSESS_RISK_URL="https://<your-foundry-host>/<risk-function-run-endpoint>"
export PALANTIR_AIP_GENERATE_MEMO_URL="https://<your-foundry-host>/<memo-function-run-endpoint>"
export PALANTIR_API_TOKEN="<your-token>"
export PALANTIR_HOSTNAME="<your-foundry-host>" # required for status checks
```

Optional controls:

```bash
export PALANTIR_FORCE_LOCAL=true
export PALANTIR_AIP_LOGIC_URL="https://<your-foundry-host>/<legacy-single-function-run-endpoint>"
```

- `PALANTIR_FORCE_LOCAL=true` skips Palantir calls and returns local-only diagnostics.
- `PALANTIR_AIP_LOGIC_URL` keeps legacy single-call recommendation mode available if you do not have staged functions yet.
- Do not commit tokens, `.env` files, or files under `apps/api/.secrets/`.

## AIP Function Contracts

Each AIP Logic function receives JSON from the backend. The backend also includes a `case_file_json` string copy of the same payload for functions that prefer a single string input.

### `extract_case_facts`

Purpose: Convert raw pasted documents, tips, emails, notes, and claim summaries into structured facts.

Environment variable:

```bash
PALANTIR_AIP_EXTRACT_FACTS_URL
```

Request shape:

```json
{
  "case": {
    "id": "case-id",
    "title": "Narrative Billing Network",
    "tip_text": "Tip text",
    "status": "draft",
    "overall_risk_score": 0,
    "created_at": "2026-04-24T00:00:00Z"
  },
  "documents": [
    {
      "id": "document-id",
      "filename": "tip-email.txt",
      "doc_type": "memo",
      "content": "Raw evidence text"
    }
  ],
  "case_file_json": "{...}"
}
```

Expected response shape:

```json
{
  "entities": [
    {
      "id": "aip-provider-1",
      "entity_type": "provider",
      "name": "Dr. Narrative Provider",
      "npi": "9999888877",
      "source": "Palantir AIP"
    }
  ],
  "claims": [
    {
      "provider_name": "Dr. Narrative Provider",
      "npi": "9999888877",
      "procedure_code": "G0483",
      "service_date": "2025-02-10",
      "amount": 7200,
      "patient_count": 94,
      "source": "Palantir AIP"
    }
  ],
  "relationships": [
    {
      "source": "Dr. Narrative Provider",
      "target": "Apex Review Group",
      "relationship": "billing_management",
      "evidence": "Apex Review Group managed billing for the provider.",
      "source_type": "Palantir AIP"
    }
  ]
}
```

### `assess_risk`

Purpose: Add Palantir-sourced risk factors after local extraction, enrichment, scoring, and graph construction.

Environment variable:

```bash
PALANTIR_AIP_ASSESS_RISK_URL
```

Request shape:

```json
{
  "case": {
    "title": "Narrative Billing Network",
    "status": "analyzed",
    "overall_risk_score": 45
  },
  "documents": [],
  "external_matches": [],
  "risk_flags": [],
  "timeline": [],
  "evidence_graph": {
    "nodes": [],
    "edges": []
  },
  "memo": {
    "title": "Draft Investigator Memo",
    "body_markdown": "Local memo",
    "source": "Local Rule"
  },
  "case_file_json": "{...}"
}
```

Expected response shape:

```json
{
  "risk_factors": [
    {
      "severity": "high",
      "reason_code": "aip_billing_network_risk",
      "score_delta": 35,
      "summary": "AIP found a billing company linkage tied to abnormal volume.",
      "why_flagged": "The provider, billing company, and claims volume form a high-risk cluster.",
      "external_validation": "Palantir AIP network and risk assessment",
      "evidence_quotes": ["Apex Review Group managed billing for the provider."]
    }
  ]
}
```

### `generate_memo`

Purpose: Replace the local template memo with a more natural investigator memo once all local and AIP risk factors are known.

Environment variable:

```bash
PALANTIR_AIP_GENERATE_MEMO_URL
```

Request shape: same structured case file used by `assess_risk`, but with merged local and AIP risk factors.

Expected response shape:

```json
{
  "title": "AIP Investigator Memo",
  "memo_markdown": "# AIP Investigator Memo\n\nPalantir AIP identified a provider-billing-company relationship and abnormal billing volume.",
  "recommendation": "Escalate for investigator review and preserve billing-company records."
}
```

## Palantir Status and Diagnostics

Check Palantir configuration status:

```bash
curl http://127.0.0.1:8000/integrations/palantir/status
```

Analyze a case with local-only mode from the API:

```bash
curl -X POST "http://127.0.0.1:8000/cases/<case_id>/analyze?force_local=true"
```

The analyze response includes:

- `palantir.mode`: `not_configured`, `forced_local`, `live`, `partial`, or `error`.
- `palantir.stages`: per-stage `configured`, `status`, `latency_ms`, `error_summary`, and `raw_response`.
- `palantir_insight`: summary recommendation for the memo panel.
- `risk_flags[].source`: `Local Rule` or `Palantir AIP`.
- `memo.source`: `Local Rule` or `Palantir AIP`.

## Foundry Ontology Notes

This repo does not require Foundry ontology object writes for the live demo. If you add persistent Foundry storage later, prefer configured Ontology Actions for writes and tenant-specific Ontology Queries for reads/searches. Do not hard-code generic object creation assumptions without your ontology API names, action API names, query API names, and permissions.

## Verification

Run tests:

```bash
npm run test
```

Run a production web build:

```bash
npm run build:web
```

Expected current verification:

- Web tests: `7 passed`
- API tests: `8 passed`
- Next.js production build: compiles successfully

## CMS Benchmark Import

The full CMS provider-service CSV is too large to commit or load at runtime. Keep the raw file outside the repo and
generate the compact benchmark artifact used by the API:

```bash
python3 scripts/build_cms_benchmarks.py \
  "/Users/daffawarsa/Downloads/Medicare Physician & Other Practitioners - by Provider and Service/2023/MUP_PHY_R25_P05_V20_D23_Prov_Svc.csv" \
  --output data/reference/cms_benchmarks.json
```

Then rerun:

```bash
npm run test:api
```
