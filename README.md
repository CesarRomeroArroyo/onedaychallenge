# ClearCSV

ClearCSV is a local MVP for Project 4 of the One Day Build Challenge. It imports a CSV, finds deterministic cleanup candidates and optional AI-assisted suggestions, then lets a person accept or reject every proposed change before export.

## Requirements

- Node.js 22.x
- pnpm 11.x
- Python 3.13 (Python 3.12–3.14 is supported by the project; Python 3.13 is the verified environment)

## Install

```bash
pnpm install
cd apps/api
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ../..
cp .env.example apps/api/.env
```

The frontend defaults to `http://localhost:8000`. To override it, create `apps/web/.env` with `VITE_API_BASE_URL`. Never put `OPENAI_API_KEY` in a `VITE_` variable.

## Run

Start API in one terminal:

```bash
cd apps/api
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Start web in another terminal:

```bash
pnpm --filter clearsv-web dev
```

Open `http://localhost:5173`. API health is shown in the upload panel.

## Configuration

Backend variables belong in `apps/api/.env`:

| Variable | Purpose |
| --- | --- |
| `WEB_URL` | Exact browser origin allowed by API CORS |
| `OPENAI_API_KEY` | Backend-only provider credential; leave empty for rules-only mode |
| `OPENAI_MODEL` | Provider model name selected by the operator |
| `AI_MODE` | `fixture` for labeled deterministic demo suggestions, or `live` for OpenAI |

`fixture` is explicitly labeled in the analysis. It is not evidence of a live provider call. In `live` mode, missing credentials leave deterministic rules available and report AI as unavailable. The configured model is not hardcoded by ClearCSV.

## Basic walkthrough

1. Click **Try sample**, or choose a UTF-8 CSV.
2. Inspect the original preview and click **Analyze data**.
3. Review findings and proposal cards. Findings without safe corrections remain visible without an Accept action.
4. Accept one proposal and reject another. Switch between **Original** and **With accepted changes**.
5. Choose faithful export, or explicitly enable spreadsheet-safe export when formula-like values need protection, then download.

The shared sample is `samples/customers-dirty.csv`; expected behavior is documented in `samples/expected-behavior.md`.

## Architecture and data safety

- `apps/web`: React/Vite/TypeScript UI, API client, contracts, upload/review/export screens.
- `apps/api`: FastAPI routes, CSV parser, in-memory dataset store, deterministic detection, OpenAI adapter, and review engine.
- Original bytes and parsed values remain immutable. Stable row and column IDs locate proposals; only accepted proposals derive the effective view and export.
- CSV values stay strings, including empty values, spaces, Unicode, dates, and leading zeros. AI receives a reproducible, bounded sample only: up to 100 rows, 10 columns, and 30,000 characters. Sensitive-looking columns are excluded heuristically; this is not guaranteed anonymization.
- Rules inspect every row. AI suggestions are validated server-side and always require human review. CSV cells are untrusted data; they are never instructions or executable content.

This MVP uses one process and volatile memory, with a 60-minute dataset TTL and at most 10 active datasets. There is no authentication, persistence, or multi-user isolation. Maximum upload is 2 MiB, 1,000 data rows, and 30 columns.

Faithful export preserves logical values and returns original bytes when no accepted change exists. Spreadsheet-safe export is opt-in and prefixes formula-like cells and headers; it changes representation and does not change review state.

## Verification

```bash
cd apps/api
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q app
cd ../web
./node_modules/.bin/tsc -p tsconfig.json --noEmit
./node_modules/.bin/vite build
```

Verified results and limitations are recorded in `docs/verification.md`. Current verification includes 8 backend tests, frontend typecheck, and production build. Playwright is not configured, and a live OpenAI smoke test remains pending until credentials and a model are supplied; fixture mode is not counted as live evidence. In this environment, pnpm's wrapper commands are blocked by its ignored `esbuild` build-script policy; direct installed binaries pass.

## Delivery materials

- `docs/demo-script.md`: five-minute English recording script.
- `docs/submission-checklist.md`: manual delivery checklist with blank repository/video fields.
- `docs/api-contract.md`: API domain and route contracts.
- `docs/plan.md`: stage decisions and real verification results.

No repository, deployment, video, or challenge form submission is created automatically.
