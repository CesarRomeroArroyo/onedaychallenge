from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import csv
import io
import re
from threading import Lock
from uuid import uuid4

from .models import Analysis, Column, Dataset, ProposalStatus, Row, ReviewSummary

TTL = timedelta(minutes=60)
MAX_DATASETS = 10


@dataclass
class StoredDataset:
    metadata: Dataset
    original_bytes: bytes
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    analysis: Analysis | None = None


class DatasetStore:
    def __init__(self) -> None:
        self._items: dict[str, StoredDataset] = {}
        self._lock = Lock()

    def create(self, filename: str, delimiter: str, headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...], raw: bytes) -> StoredDataset:
        now = datetime.now(UTC)
        with self._lock:
            self._purge_expired(now)
            if len(self._items) >= MAX_DATASETS:
                raise RuntimeError("Dataset capacity is full; delete an active dataset and retry.")
            dataset_id = uuid4().hex
            columns = tuple(Column(id=f"col_{index}_{uuid4().hex[:8]}", original_header=header, position=index) for index, header in enumerate(headers))
            metadata = Dataset(id=dataset_id, filename=_safe_filename(filename), created_at=now, expires_at=now + TTL, delimiter=delimiter, columns=list(columns), row_count=len(rows), revision=0)
            stored = StoredDataset(metadata=metadata, original_bytes=bytes(raw), headers=headers, rows=rows)
            self._items[dataset_id] = stored
            return stored

    def get(self, dataset_id: str) -> StoredDataset | None:
        with self._lock:
            self._purge_expired(datetime.now(UTC))
            return self._items.get(dataset_id)

    def delete(self, dataset_id: str) -> bool:
        with self._lock:
            return self._items.pop(dataset_id, None) is not None

    def rows(self, stored: StoredDataset, view: str = "original") -> list[Row]:
        values_by_row = [list(values) for values in stored.rows]
        excluded: set[str] = set()
        if view == "effective" and stored.analysis:
            for proposal in stored.analysis.proposals:
                if proposal.status != ProposalStatus.ACCEPTED:
                    continue
                index = int(proposal.row_id.removeprefix("row_"))
                if proposal.action.value == "exclude_row":
                    excluded.add(proposal.row_id)
                elif proposal.column_id and proposal.proposed_value is not None:
                    column_index = next(column.position for column in stored.metadata.columns if column.id == proposal.column_id)
                    values_by_row[index][column_index] = proposal.proposed_value
        return [Row(id=f"row_{index}", source_record_number=index + 2, values={column.id: values_by_row[index][column.position] for column in stored.metadata.columns}) for index in range(len(values_by_row)) if f"row_{index}" not in excluded]

    def update_analysis(self, dataset_id: str, analysis: Analysis) -> StoredDataset:
        with self._lock:
            stored = self._items[dataset_id]
            stored.analysis = analysis
            return stored

    def review(self, dataset_id: str, expected_revision: int, decisions: dict[str, tuple[ProposalStatus, str | None]]) -> ReviewSummary:
        with self._lock:
            stored = self._items.get(dataset_id)
            if stored is None:
                raise KeyError(dataset_id)
            if stored.metadata.revision != expected_revision:
                raise ValueError("Revision is stale; refresh the dataset before reviewing proposals.")
            if stored.analysis is None:
                raise ValueError("Dataset must be analyzed before proposals can be reviewed.")
            proposals = {proposal.id: proposal for proposal in stored.analysis.proposals}
            if any(proposal_id not in proposals for proposal_id in decisions):
                raise LookupError("Review contains an unknown proposal.")
            proposed = list(proposals.values())
            candidate_statuses = {proposal.id: decisions.get(proposal.id, (proposal.status, None))[0] for proposal in proposed}
            accepted = [proposal for proposal in proposed if candidate_statuses[proposal.id] == ProposalStatus.ACCEPTED]
            cell_targets: set[tuple[str, str]] = set()
            excluded: set[str] = set()
            for proposal in accepted:
                if proposal.action.value == "exclude_row":
                    excluded.add(proposal.row_id)
                elif proposal.column_id is not None:
                    target = (proposal.row_id, proposal.column_id)
                    if target in cell_targets:
                        raise RuntimeError("Conflicting accepted proposals target the same cell.")
                    cell_targets.add(target)
            if any(proposal.row_id in excluded and proposal.action.value == "set_cell" for proposal in accepted):
                raise RuntimeError("A row cannot be excluded and edited in the same review.")
            changed = any(candidate_statuses[proposal.id] != proposal.status or decisions.get(proposal.id, (proposal.status, None))[1] is not None for proposal in proposed)
            for proposal in proposed:
                edited_value = decisions.get(proposal.id, (proposal.status, None))[1]
                if edited_value is not None:
                    if proposal.proposed_value is None:
                        raise ValueError("Proposal does not support edited values.")
                    proposal.proposed_value = edited_value
                proposal.status = candidate_statuses[proposal.id]
            if changed:
                stored.metadata.revision += 1
            return ReviewSummary(
                revision=stored.metadata.revision,
                accepted=len(accepted),
                rejected=sum(proposal.status == ProposalStatus.REJECTED for proposal in proposed),
                pending=sum(proposal.status == ProposalStatus.PENDING for proposal in proposed),
                excluded_rows=len(excluded),
            )

    def export(self, dataset_id: str, mode: str = "faithful") -> tuple[bytes, str]:
        with self._lock:
            stored = self._items.get(dataset_id)
            if stored is None:
                raise KeyError(dataset_id)
            if mode not in {"faithful", "spreadsheet_safe"}:
                raise ValueError("Export mode must be faithful or spreadsheet_safe.")
            if mode == "faithful" and not _has_accepted_changes(stored):
                return stored.original_bytes, stored.metadata.filename
            values = [list(row) for row in stored.rows]
            excluded: set[str] = set()
            if stored.analysis:
                for proposal in stored.analysis.proposals:
                    if proposal.status != ProposalStatus.ACCEPTED:
                        continue
                    row_index = int(proposal.row_id.removeprefix("row_"))
                    if proposal.action.value == "exclude_row":
                        excluded.add(proposal.row_id)
                    elif proposal.column_id and proposal.proposed_value is not None:
                        column_index = next(column.position for column in stored.metadata.columns if column.id == proposal.column_id)
                        values[row_index][column_index] = proposal.proposed_value
            headers = list(stored.headers)
            if mode == "spreadsheet_safe":
                headers = [_safe_spreadsheet_value(value) for value in headers]
                values = [[_safe_spreadsheet_value(value) for value in row] for row in values]
            output = io.StringIO(newline="")
            writer = csv.writer(output, delimiter=stored.metadata.delimiter, lineterminator="\r\n")
            writer.writerow(headers)
            writer.writerows(row for index, row in enumerate(values) if f"row_{index}" not in excluded)
            return output.getvalue().encode("utf-8"), stored.metadata.filename

    def _purge_expired(self, now: datetime) -> None:
        expired = [key for key, value in self._items.items() if value.metadata.expires_at <= now]
        for key in expired:
            del self._items[key]


def _safe_filename(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    return name[:255] or "uploaded.csv"


def _has_accepted_changes(stored: StoredDataset) -> bool:
    return bool(stored.analysis and any(proposal.status == ProposalStatus.ACCEPTED for proposal in stored.analysis.proposals))


_FORMULA_VALUE = re.compile(r"^[\s\x00-\x1f]*[=+\-@]")


def _safe_spreadsheet_value(value: str) -> str:
    return f"'{value}" if _FORMULA_VALUE.match(value) else value
