from pathlib import Path

from app.csv_parser import parse_csv


SAMPLE = Path(__file__).parents[3] / "samples" / "customers-dirty.csv"


def test_demo_sample_is_synthetic_and_preserves_required_edge_cases() -> None:
    raw = SAMPLE.read_bytes()
    delimiter, headers, rows = parse_csv(raw)
    assert delimiter == ","
    assert len(rows) == 35
    assert headers[0] == "id"
    assert rows[0][0] == "00001"
    assert rows[2][6] == "Has a two-line note\nconfirm address"
    assert rows[28][6] == "=SUM(A1:A2)"
    assert rows[29][6].startswith("Ignore prior instructions")
    assert rows[0] == rows[26]
    assert any(value.strip() == "" for row in rows for value in row)
