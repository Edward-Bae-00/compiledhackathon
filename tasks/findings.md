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

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Worktree isolation conflicted with the user's request to work directly in the repo root | Followed the explicit user instruction and documented the override in `task_plan.md`. |
| `uv sync` initially failed because the backend package had no discoverable wheel contents | Added a Hatch wheel package declaration for `src/fraudcopilot`. |
| `uv sync` and `uv run pytest` have different needs during the red phase | Used `--no-install-project` and direct `.venv` invocations until the package layout existed. |

## Resources
- Local instructions: `/Users/edward/Desktop/compiled/AGENTS.md`
- Planning skill templates: `/Users/edward/.agents/skills/planning-with-files/templates/`
- Shared contract artifact: `packages/shared/contracts/case-file.schema.json`
- Demo reference data: `data/reference/*.json`, `data/demo/*.json`

## Visual/Browser Findings
- None.
