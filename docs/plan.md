# ClearCSV implementation plan

## Scope

ClearCSV loads a CSV, identifies deterministic and AI-assisted cleanup candidates, lets a user review proposals, and exports only accepted changes. This repository is a local, single-process MVP with volatile memory.

## Stages

| Stage | Goal | Acceptance | Status |
| --- | --- | --- | --- |
| P-01 | Executable web/API base and contracts | Web starts, API health responds, typecheck/build pass, configuration has no secrets | Completed |
| P-02 | CSV import, limits, preview, TTL | Real CSV values preserved and preview/deletion work | Completed |
| P-03 | Deterministic detection and review engine | Proposals and atomic decisions preserve original data | Completed |
| P-04 | Real AI integration and validation | Provider output is validated and coverage is honest | Completed |
| P-05 | Complete review UI and export | Upload → analyze → review → export works | Completed |
| P-06 | Synthetic sample and integration verification | Focused tests and E2E flow pass | Completed |
| P-07 | README and delivery materials | Reproducible documentation and demo script exist | Completed |

## Decisions

- Monorepo layout: `apps/web` for Vite React and `apps/api` for FastAPI.
- Frontend uses pnpm workspace scripts; backend uses a pinned `requirements.txt` plus `pyproject.toml`.
- API contracts are duplicated intentionally as small Pydantic and TypeScript models; no generator is introduced for this one-day MVP.
- API implementation begins with `GET /api/health`. Future routes are documented in `docs/api-contract.md` but are not stubbed as successful endpoints.
- CORS allows only `WEB_URL`, defaulting to `http://localhost:5173` for local development; no wildcard is used.

## P-01 verification

- Environment inspected: Node 22.22.1, pnpm 11.25.0, Python 3.14.7 default and Python 3.13.2 available for the backend environment.
- `pnpm install`: dependency graph and `pnpm-lock.yaml` created; pnpm reported ignored esbuild build scripts in this environment.
- `apps/web`: `./node_modules/.bin/tsc -p tsconfig.json --noEmit` passed; `./node_modules/.bin/vite build` passed.
- `apps/api`: Python 3.13 virtual environment installed pinned requirements; FastAPI TestClient `GET /api/health` returned HTTP 200 and expected JSON.
- CORS smoke: live Uvicorn `OPTIONS /api/health` from `http://localhost:5173` returned HTTP 200 with matching allow-origin and requested headers.
- Known environment note: Python 3.14 cannot build pinned `pydantic-core==2.33.2` here; documented backend command uses Python 3.13 when available.

## P-02 implementation and verification

- `apps/api/app/csv_parser.py` reads UTF-8/BOM CSV through Python's `csv` parser, preserves values as strings, supports comma/semicolon selection, quoted and multiline fields, and rejects malformed structure and 2 MiB/1,000-row/30-column limits. Completely blank physical lines are ignored by the standard parser; empty cells remain values.
- `apps/api/app/store.py` keeps immutable original bytes and parsed tuples in process memory, applies 60-minute expiry and a 10-dataset capacity, sanitizes only the displayed filename, and creates stable column/row IDs.
- `POST /api/datasets`, paginated `GET /api/datasets/{id}/rows`, and `DELETE /api/datasets/{id}` are implemented. Frontend now uploads real files and renders server preview.
- `apps/api/.venv/bin/python -m pytest`: 3 passed (one existing Starlette deprecation warning).
- `apps/api/.venv/bin/python -m compileall -q app`: passed.
- `apps/web/node_modules/.bin/tsc -p tsconfig.json --noEmit`: passed.
- `apps/web/node_modules/.bin/vite build`: passed.
- `pnpm --filter clearsv-web typecheck/build` could not complete because this environment blocks the ignored `esbuild` install script; direct binaries passed.

## P-03 implementation and verification

- `apps/api/app/detection.py` performs deterministic duplicate, missing, whitespace/category, suspicious email, and ambiguous date detection. It never invents missing values and marks every proposal as pending.
- `DatasetStore` retains immutable source tuples, stores analysis results, derives `effective` rows from accepted proposals, and applies review batches under a lock with revision checks and conflict validation.
- API routes now implement analyze, analysis retrieval, effective/original preview, and atomic review. Repeated decisions are idempotent; stale revisions and incompatible accepted proposals return conflicts.

## P-04 implementation and verification

- `apps/api/app/ai.py` defines `AIAnalyzer`, explicit fixture mode, and OpenAI Chat Completions integration using configured `OPENAI_MODEL`, 30-second timeout, one SDK retry, and structured JSON validation.
- AI receives at most 100 selected stable row IDs, 10 columns, and 30,000 characters. Protected email/phone/document/password/token/secret columns are excluded from values. Findings are validated against payload IDs and immutable original values before becoming pending AI issues/proposals.
- Missing live credentials preserve deterministic analysis and add an honest unavailable warning. Fixture mode is explicitly labeled in analysis warnings; no fixture is presented as a provider call.
- `apps/api/tests/test_ai.py` covers protected payload omission, stable IDs, and invalid provider findings. `apps/api/.venv/bin/python -m pytest`: 7 passed (one existing Starlette deprecation warning). `apps/api/.venv/bin/python -m compileall -q app`: passed. Frontend typecheck and Vite build: passed.

## P-05 implementation and verification

- Frontend now presents upload, dataset metadata, explicit AI sample disclosure, analysis coverage, findings without forced fixes, original/effective views, proposal cards, filters-by-status through review state, and atomic Accept/Reject actions.
- `GET /api/datasets/{id}/export` writes accepted edits/exclusions only. Faithful mode returns immutable original bytes when unchanged; spreadsheet-safe mode is explicit and prefixes formula-like values and headers.
- Verification: `apps/api/.venv/bin/python -m pytest` => 7 passed; `apps/api/.venv/bin/python -m compileall -q apps/api/app` => passed; `apps/web/./node_modules/.bin/tsc -p tsconfig.json --noEmit` => passed; `apps/web/./node_modules/.bin/vite build` => passed; TestClient upload → analyze → accept → export smoke => passed. Existing Starlette deprecation warning remains.

## P-06 implementation and verification

- Added `samples/customers-dirty.csv` with 35 synthetic records and `samples/expected-behavior.md` documenting exact locations, preservation requirements, and AI invariants.
- Added `Try sample` to the existing upload flow. Vite serves the shared sample file from `samples`, and the button sends it through the same upload API as a user-selected file.
- Added `apps/api/tests/test_sample.py`; it uses the production parser to verify row count, duplicate fixture, leading zeros, Unicode, multiline content, formula-like data, instruction-like data, and blank values.
- `apps/api/.venv/bin/python -m pytest`: 8 passed; existing Starlette deprecation warning remains.
- `apps/web/./node_modules/.bin/tsc -p tsconfig.json --noEmit`: passed.
- `apps/web/./node_modules/.bin/vite build`: passed and copied the sample into `dist`.
- Playwright is not configured, so browser E2E was not run. Live OpenAI smoke remains unavailable without credentials; no fixture was counted as live evidence. Full details: `docs/verification.md`.

## P-07 implementation and verification

- Added English `README.md` with clean-clone installation, exact API/frontend commands, environment configuration, fixture/live distinction, architecture, limits, data handling, verification, and delivery links.
- Added `docs/demo-script.md` with a five-minute walkthrough and honest provider-error fallback.
- Added `docs/submission-checklist.md` with blank repository/video fields and the challenge form URL; no publication, recording, or submission was performed.
- Verification: `pnpm install --offline` resolved the lockfile but exited with pnpm's existing ignored `esbuild` build-script policy; no dependency changes were needed. Backend `pytest` and `compileall` passed; direct frontend `tsc` and `vite build` passed. The pnpm filter wrappers hit the same environment policy. Live OpenAI smoke and browser E2E remain unavailable because credentials/model and Playwright are not configured.
