import csv
import io

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1_000
MAX_COLUMNS = 30
SUPPORTED_DELIMITERS = {",", ";"}


class CsvImportError(ValueError):
    def __init__(self, message: str, code: str = "invalid_csv") -> None:
        super().__init__(message)
        self.code = code


def parse_csv(raw: bytes, requested_delimiter: str | None = None) -> tuple[str, tuple[str, ...], tuple[tuple[str, ...], ...]]:
    if not raw:
        raise CsvImportError("CSV file is empty.")
    if len(raw) > MAX_BYTES:
        raise CsvImportError("CSV file exceeds the 2 MiB limit.", "file_too_large")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvImportError("CSV must use UTF-8 encoding.", "invalid_encoding") from exc

    delimiter = requested_delimiter or _detect_delimiter(text)
    if delimiter not in SUPPORTED_DELIMITERS:
        raise CsvImportError("Delimiter must be comma or semicolon.", "invalid_delimiter")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        headers = tuple(next(reader))
    except StopIteration as exc:
        raise CsvImportError("CSV file has no header.") from exc
    if not headers or len(headers) > MAX_COLUMNS:
        raise CsvImportError("CSV must contain between 1 and 30 columns.", "column_limit")

    rows: list[tuple[str, ...]] = []
    for record_number, row in enumerate(reader, start=2):
        if len(row) != len(headers):
            raise CsvImportError(f"Record {record_number} has {len(row)} fields; expected {len(headers)}.")
        rows.append(tuple(row))
        if len(rows) > MAX_ROWS:
            raise CsvImportError("CSV exceeds the 1,000 data-row limit.", "row_limit")
    if not rows:
        raise CsvImportError("CSV must contain at least one data row.")
    return delimiter, headers, tuple(rows)


def _detect_delimiter(text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(text[:32_768], delimiters=",;")
    except csv.Error as exc:
        first_line = text.splitlines()[0] if text.splitlines() else ""
        comma_count, semicolon_count = first_line.count(","), first_line.count(";")
        if comma_count > 0 and semicolon_count == 0:
            return ","
        if semicolon_count > 0 and comma_count == 0:
            return ";"
        raise CsvImportError("Could not detect delimiter; choose comma or semicolon.", "ambiguous_delimiter") from exc
    if sum(line.count(",") for line in text.splitlines()) == sum(line.count(";") for line in text.splitlines()):
        raise CsvImportError("Could not determine delimiter; choose comma or semicolon.", "ambiguous_delimiter")
    return dialect.delimiter
