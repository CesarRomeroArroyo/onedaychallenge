from app.ai import AIResponse, build_payload, validate_findings
from app.models import AIFinding, IssueCategory, ProposalAction
from app.store import DatasetStore


def make_dataset():
    return DatasetStore().create(
        "data.csv",
        ",",
        ("id", "name", "email"),
        (("001", " Ana ", "ana@example.com"),),
        b"id,name,email\n001, Ana ,ana@example.com\n",
    )


def test_ai_payload_excludes_protected_values_and_keeps_stable_ids() -> None:
    payload = build_payload(make_dataset(), ["row_0"])
    assert len(payload["rows"]) == 1
    assert " Ana " in payload["rows"][0]["values"].values()
    assert all(column["header"] != "email" for column in payload["columns"])


def test_invalid_ai_ids_and_original_values_are_discarded() -> None:
    dataset = make_dataset()
    name_id = dataset.metadata.columns[1].id
    response = AIResponse(suggestions=[
        AIFinding(category=IssueCategory.INCONSISTENT, row_id="row_999", column_id=name_id, action=ProposalAction.SET_CELL, original_value=" Ana ", proposed_value="Ana", explanation="unknown row"),
        AIFinding(category=IssueCategory.INCONSISTENT, row_id="row_0", column_id=name_id, action=ProposalAction.SET_CELL, original_value="wrong", proposed_value="Ana", explanation="wrong original"),
        AIFinding(category=IssueCategory.INCONSISTENT, row_id="row_0", column_id=name_id, action=ProposalAction.SET_CELL, original_value=" Ana ", proposed_value="Ana", explanation="valid"),
    ])
    findings = validate_findings(response, dataset, ["row_0"])
    assert len(findings) == 1
    assert findings[0].proposed_value == "Ana"
