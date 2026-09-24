from fastapi.testclient import TestClient

from app.csv_parser import CsvImportError, parse_csv
from app.main import app


def test_parser_preserves_text_quotes_unicode_and_multiline() -> None:
    delimiter, headers, rows = parse_csv('id,name,note\n00123,José,"line one\nline two"\n'.encode())
    assert delimiter == ","
    assert headers == ("id", "name", "note")
    assert rows == (("00123", "José", "line one\nline two"),)


def test_parser_rejects_bad_record_shape() -> None:
    try:
        parse_csv(b"a,b\n1\n")
    except CsvImportError as exc:
        assert "Record 2" in str(exc)
    else:
        raise AssertionError("expected malformed record to be rejected")


def test_upload_preview_and_delete() -> None:
    client = TestClient(app)
    response = client.post("/api/datasets", files={"file": ("../customers.csv", b"id,name\n001,Ana\n", "text/csv")})
    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset"]["filename"] == "customers.csv"
    assert payload["preview"][0]["values"][payload["dataset"]["columns"][0]["id"]] == "001"
    dataset_id = payload["dataset"]["id"]
    assert client.get(f"/api/datasets/{dataset_id}/rows").json()["total"] == 1
    assert client.delete(f"/api/datasets/{dataset_id}").status_code == 204
    assert client.get(f"/api/datasets/{dataset_id}/rows").status_code == 404


def test_analysis_and_review_derive_effective_rows_without_mutating_original() -> None:
    client = TestClient(app)
    response = client.post("/api/datasets", files={"file": ("dirty.csv", b"id,city,email\n001,Madrid,ok@example.com\n001,Madrid,ok@example.com\n002, Madrid ,broken\n", "text/csv")})
    dataset = response.json()["dataset"]
    dataset_id = dataset["id"]
    analysis = client.post(f"/api/datasets/{dataset_id}/analyze").json()
    assert analysis["rules_rows_checked"] == 3
    assert any(issue["category"] == "duplicate" for issue in analysis["issues"])
    trim = next(proposal for proposal in analysis["proposals"] if proposal["action"] == "set_cell")
    duplicate = next(proposal for proposal in analysis["proposals"] if proposal["action"] == "exclude_row")
    review = client.post(f"/api/datasets/{dataset_id}/review", json={"expected_revision": 0, "decisions": [{"proposal_id": trim["id"], "decision": "accepted"}, {"proposal_id": duplicate["id"], "decision": "accepted"}]})
    assert review.status_code == 200
    original = client.get(f"/api/datasets/{dataset_id}/rows?view=original").json()
    effective = client.get(f"/api/datasets/{dataset_id}/rows?view=effective").json()
    assert original["total"] == 3
    assert effective["total"] == 2
    assert original["items"][2]["values"][dataset["columns"][1]["id"]] == " Madrid "


def test_review_batch_is_atomic_on_stale_revision() -> None:
    client = TestClient(app)
    dataset = client.post("/api/datasets", files={"file": ("dirty.csv", b"id,name\n1,Ana \n2,Bob\n", "text/csv")}).json()["dataset"]
    dataset_id = dataset["id"]
    proposals = client.post(f"/api/datasets/{dataset_id}/analyze").json()["proposals"]
    payload = {"expected_revision": 0, "decisions": [{"proposal_id": proposals[0]["id"], "decision": "accepted"}]}
    assert client.post(f"/api/datasets/{dataset_id}/review", json=payload).status_code == 200
    assert client.post(f"/api/datasets/{dataset_id}/review", json=payload).status_code == 409
