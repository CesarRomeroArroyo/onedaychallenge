from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .csv_parser import CsvImportError, MAX_BYTES, parse_csv
from .ai import FixtureAnalyzer, OpenAIAnalyzer, select_rows, validate_findings
from .detection import analyze, apply_ai_findings
from .models import ReviewRequest
from .store import DatasetStore
from fastapi.responses import Response

app = FastAPI(title="ClearCSV API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

store = DatasetStore()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "clearsv-api"}


@app.post("/api/datasets")
async def upload_dataset(file: UploadFile = File(...), delimiter: str | None = Form(default=None)) -> dict[str, object]:
    raw = bytearray()
    while chunk := await file.read(64 * 1024):
        raw.extend(chunk)
        if len(raw) > MAX_BYTES:
            raise HTTPException(status_code=413, detail={"code": "file_too_large", "message": "CSV file exceeds the 2 MiB limit.", "details": None})
    try:
        detected, headers, rows = parse_csv(bytes(raw), delimiter)
        stored = store.create(file.filename or "uploaded.csv", detected, headers, rows, bytes(raw))
    except CsvImportError as exc:
        status = 413 if exc.code in {"file_too_large", "row_limit", "column_limit"} else 422
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc), "details": None}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "capacity_full", "message": str(exc), "details": None}) from exc
    preview = store.rows(stored)[:5]
    return {"dataset": stored.metadata.model_dump(mode="json"), "preview": [row.model_dump() for row in preview]}


@app.get("/api/datasets/{dataset_id}/rows")
def get_rows(dataset_id: str, page: int = 1, page_size: int = 50, view: str = "original") -> dict[str, object]:
    stored = store.get(dataset_id)
    if stored is None:
        raise HTTPException(status_code=404, detail={"code": "dataset_not_found", "message": "Dataset not found or expired.", "details": None})
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_pagination", "message": "Page must be positive and page_size must be between 1 and 100.", "details": None})
    if view not in {"original", "effective"}:
        raise HTTPException(status_code=422, detail={"code": "invalid_view", "message": "View must be original or effective.", "details": None})
    rows = store.rows(stored, view)
    start = (page - 1) * page_size
    return {"items": [row.model_dump() for row in rows[start : start + page_size]], "page": page, "page_size": page_size, "total": len(rows), "view": view}


@app.delete("/api/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str) -> None:
    if not store.delete(dataset_id):
        raise HTTPException(status_code=404, detail={"code": "dataset_not_found", "message": "Dataset not found or expired.", "details": None})


@app.post("/api/datasets/{dataset_id}/analyze")
def analyze_dataset(dataset_id: str) -> dict[str, object]:
    stored = store.get(dataset_id)
    if stored is None:
        raise HTTPException(status_code=404, detail={"code": "dataset_not_found", "message": "Dataset not found or expired.", "details": None})
    if stored.analysis is None:
        result = analyze(stored)
        candidate_ids = [row_id for issue in result.issues for row_id in issue.row_ids]
        selected_ids = select_rows(stored, candidate_ids)
        if settings.ai_mode == "fixture":
            analyzer = FixtureAnalyzer()
            result.warnings.append("AI fixture mode is active; no external provider was called.")
        elif settings.ai_mode == "live" and settings.openai_api_key and settings.openai_model:
            analyzer = OpenAIAnalyzer()
        else:
            analyzer = None
            result.warnings.append("AI unavailable: configure OPENAI_API_KEY and OPENAI_MODEL to enable live review.")
        if analyzer is not None:
            try:
                ai_response, ai_rows, ai_columns = analyzer.analyze(stored, selected_ids)
                result.ai_rows_reviewed = ai_rows
                result.ai_columns_reviewed = ai_columns
                apply_ai_findings(result, validate_findings(ai_response, stored, selected_ids))
            except Exception:
                result.warnings.append("AI unavailable: provider response could not be validated.")
        store.update_analysis(dataset_id, result)
    return store.get(dataset_id).analysis.model_dump(mode="json")  # type: ignore[union-attr]


@app.get("/api/datasets/{dataset_id}/analysis")
def get_analysis(dataset_id: str) -> dict[str, object]:
    stored = store.get(dataset_id)
    if stored is None:
        raise HTTPException(status_code=404, detail={"code": "dataset_not_found", "message": "Dataset not found or expired.", "details": None})
    if stored.analysis is None:
        raise HTTPException(status_code=409, detail={"code": "analysis_required", "message": "Analyze dataset before requesting results.", "details": None})
    return stored.analysis.model_dump(mode="json")


@app.post("/api/datasets/{dataset_id}/review")
def review_dataset(dataset_id: str, request: ReviewRequest) -> dict[str, object]:
    decisions = {decision.proposal_id: decision.decision for decision in request.decisions}
    try:
        summary = store.review(dataset_id, request.expected_revision, decisions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "dataset_not_found", "message": "Dataset not found or expired.", "details": None}) from exc
    except ValueError as exc:
        status = 409 if "Revision" in str(exc) else 422
        raise HTTPException(status_code=status, detail={"code": "review_conflict", "message": str(exc), "details": None}) from exc
    except LookupError as exc:
        raise HTTPException(status_code=422, detail={"code": "unknown_proposal", "message": str(exc), "details": None}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "proposal_conflict", "message": str(exc), "details": None}) from exc
    return summary.model_dump(mode="json")


@app.get("/api/datasets/{dataset_id}/export")
def export_dataset(dataset_id: str, mode: str = "faithful") -> Response:
    try:
        content, filename = store.export(dataset_id, mode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "dataset_not_found", "message": "Dataset not found or expired.", "details": None}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_export_mode", "message": str(exc), "details": None}) from exc
    return Response(content=content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
