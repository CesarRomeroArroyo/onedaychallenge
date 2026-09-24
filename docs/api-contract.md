# API contract

P-01 exposes `GET /api/health`, returning `{ "status": "ok", "service": "clearsv-api" }`.

The domain models in `apps/api/app/models.py` and `apps/web/src/contracts.ts` define the shared shape for Dataset, Column, Row, Issue, Proposal, Analysis, and ReviewRequest. IDs are opaque strings; CSV values remain strings.

P-02 implements `POST /api/datasets`, paginated `GET /api/datasets/{id}/rows`, and `DELETE /api/datasets/{id}`. Upload returns `{ dataset, preview }`; preview contains first five parsed rows. `POST /api/datasets` accepts multipart `file` and optional `delimiter` (`\,` or `;`).

P-03 implements synchronous `POST /api/datasets/{id}/analyze`, `GET /api/datasets/{id}/analysis`, and atomic `POST /api/datasets/{id}/review`. Rules detect exact duplicates, missing cells, safe text whitespace/category variants, suspicious emails, and ambiguous dates. Original rows remain immutable; `view=effective` derives accepted edits and exclusions.

P-04 runs rules over every row, then sends at most 100 selected rows and 10 non-sensitive columns (30,000 characters) to one configured AI call. `Analysis` reports `rules_rows_checked`, `ai_rows_reviewed`, `ai_columns_reviewed`, and sanitized `warnings`. `AI_MODE=fixture` is explicit local/test mode; `AI_MODE=live` requires `OPENAI_API_KEY` and `OPENAI_MODEL`. Provider JSON is validated server-side against stable IDs and original values before becoming pending, human-reviewed findings.

Review requests contain only `expected_revision` and proposal IDs with `pending`, `accepted`, or `rejected` decisions. The server validates all IDs and conflicts before applying the batch. A stale revision returns 409.

P-05 implements `GET /api/datasets/{id}/export?mode=faithful|spreadsheet_safe`. Faithful mode returns original bytes when no proposal is accepted; otherwise it writes accepted edits and exclusions with the input delimiter. Spreadsheet-safe mode prefixes formula-like headers and cells with an apostrophe and is opt-in.

Errors will use `{ "code": string, "message": string, "details": object | null }`; planned status codes include 404, 409, 413, and 422. No route returns a successful fake implementation.
