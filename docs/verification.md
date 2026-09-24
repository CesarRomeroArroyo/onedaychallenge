# Verification

## P-06 results

- `apps/api/.venv/bin/python -m pytest` from `apps/api`: **8 passed**; one existing Starlette `DeprecationWarning`.
- `apps/api/.venv/bin/python -m compileall -q app`: not rerun in P-06; unchanged backend modules are covered by pytest import.
- `apps/web/node_modules/.bin/tsc -p tsconfig.json --noEmit` from `apps/web`: **passed**.
- `apps/web/node_modules/.bin/vite build` from `apps/web`: **passed**; build includes `customers-dirty.csv` from the shared `samples` directory.

## Coverage and limitations

- `samples/customers-dirty.csv` contains 35 synthetic records covering exact duplicates, blank values, whitespace, Unicode, malformed email, leading-zero IDs, ambiguous dates, formula-looking content, multiline CSV content, and an instruction-like cell.
- The sample test parses the file through the production CSV parser and checks preservation invariants.
- Playwright is not configured in this repository, so browser E2E upload/analyze/review/download was not executed in this stage.
- No live OpenAI smoke was executed because `OPENAI_API_KEY` and `OPENAI_MODEL` are not configured. Fixture mode remains explicitly labeled.

## P-07 results

- `pnpm install --offline`: lockfile was up to date, but pnpm exited with `ERR_PNPM_IGNORED_BUILDS` for `esbuild@0.25.12`; this is an environment policy issue, not an application failure. No lockfile change was required.
- `apps/api/.venv/bin/python -m pytest` and `apps/api/.venv/bin/python -m compileall -q app`: **8 passed** and compile completed; existing Starlette deprecation warning remains.
- `apps/web/node_modules/.bin/tsc --noEmit`: **passed**.
- `apps/web/node_modules/.bin/vite build`: **passed**; sample copied into `dist`.
- `pnpm --filter clearsv-web typecheck/build` was attempted and hit the same ignored `esbuild` build-script policy. Direct installed binaries above provide successful frontend verification.
