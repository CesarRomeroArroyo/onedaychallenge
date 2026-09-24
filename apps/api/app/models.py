from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class IssueCategory(StrEnum):
    DUPLICATE = "duplicate"
    INCONSISTENT = "inconsistent"
    MISSING = "missing"
    SUSPICIOUS = "suspicious"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProposalAction(StrEnum):
    SET_CELL = "set_cell"
    EXCLUDE_ROW = "exclude_row"


class ProposalStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Column(BaseModel):
    id: str
    original_header: str
    position: int = Field(ge=0)


class Row(BaseModel):
    id: str
    source_record_number: int = Field(ge=1)
    values: dict[str, str]


class Dataset(BaseModel):
    id: str
    filename: str
    created_at: datetime
    expires_at: datetime
    delimiter: str
    columns: list[Column]
    row_count: int = Field(ge=0)
    revision: int = Field(ge=0)


class Issue(BaseModel):
    id: str
    category: IssueCategory
    severity: Severity
    row_ids: list[str]
    column_id: str | None = None
    explanation: str
    source: str
    proposal_id: str | None = None


class Proposal(BaseModel):
    id: str
    action: ProposalAction
    row_id: str
    column_id: str | None = None
    original_value: str
    proposed_value: str | None = None
    reason: str
    source: str
    status: ProposalStatus
    confidence: float | None = None


class Analysis(BaseModel):
    status: str
    rules_rows_checked: int = 0
    ai_rows_reviewed: int = 0
    ai_columns_reviewed: int = 0
    warnings: list[str] = []
    issues: list[Issue] = []
    proposals: list[Proposal] = []


class AIFinding(BaseModel):
    category: IssueCategory
    row_id: str
    column_id: str | None = None
    action: ProposalAction | None = None
    original_value: str = ""
    proposed_value: str | None = None
    explanation: str = Field(min_length=1, max_length=500)


class ReviewSummary(BaseModel):
    revision: int
    accepted: int
    rejected: int
    pending: int
    excluded_rows: int


class ReviewDecision(BaseModel):
    proposal_id: str
    decision: ProposalStatus


class ReviewRequest(BaseModel):
    expected_revision: int = Field(ge=0)
    decisions: list[ReviewDecision]
