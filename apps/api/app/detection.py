import re
from collections import defaultdict
from uuid import uuid4

from .models import AIFinding, Analysis, Issue, IssueCategory, Proposal, ProposalAction, ProposalStatus, Severity
from .store import StoredDataset

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DATE_RE = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")


def analyze(stored: StoredDataset) -> Analysis:
    columns = stored.metadata.columns
    rows = [dict(zip((column.id for column in columns), values)) for values in stored.rows]
    row_ids = [f"row_{index}" for index in range(len(rows))]
    issues: list[Issue] = []
    proposals: list[Proposal] = []

    def add_proposal(action: ProposalAction, row_id: str, column_id: str | None, original: str, proposed: str | None, reason: str) -> None:
        if action == ProposalAction.SET_CELL and proposed == original:
            return
        if any(p.action == action and p.row_id == row_id and p.column_id == column_id and p.proposed_value == proposed for p in proposals):
            return
        proposals.append(Proposal(id=f"prop_{uuid4().hex}", action=action, row_id=row_id, column_id=column_id, original_value=original, proposed_value=proposed, reason=reason, source="rule", status=ProposalStatus.PENDING))

    groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[tuple(row[column.id] for column in columns)].append(index)
    for duplicate_rows in groups.values():
        if len(duplicate_rows) < 2:
            continue
        ids = [row_ids[index] for index in duplicate_rows]
        issue_id = f"issue_{uuid4().hex}"
        issue = Issue(id=issue_id, category=IssueCategory.DUPLICATE, severity=Severity.WARNING, row_ids=ids, explanation="Rows have identical original values.", source="rule")
        for index in duplicate_rows[1:]:
            add_proposal(ProposalAction.EXCLUDE_ROW, row_ids[index], None, "", None, f"Duplicate of {row_ids[duplicate_rows[0]]}; review before excluding.")
        issue.proposal_id = next((p.id for p in proposals if p.row_id in ids[1:] and p.action == ProposalAction.EXCLUDE_ROW), None)
        issues.append(issue)

    for column in columns:
        values = [row[column.id] for row in rows]
        header = column.original_header.strip().lower()
        protected = any(token in header for token in ("id", "email", "phone", "telephone", "document", "password", "token", "secret"))
        for index, value in enumerate(values):
            row_id = row_ids[index]
            if not value or not value.strip():
                issues.append(Issue(id=f"issue_{uuid4().hex}", category=IssueCategory.MISSING, severity=Severity.WARNING, row_ids=[row_id], column_id=column.id, explanation="Cell is empty or contains only whitespace; no value was invented.", source="rule"))
            if not protected and value != value.strip() and value.strip():
                proposal = Proposal(id=f"prop_{uuid4().hex}", action=ProposalAction.SET_CELL, row_id=row_id, column_id=column.id, original_value=value, proposed_value=value.strip(), reason="Remove external whitespace from a common text field.", source="rule", status=ProposalStatus.PENDING)
                proposals.append(proposal)
                issues.append(Issue(id=f"issue_{uuid4().hex}", category=IssueCategory.INCONSISTENT, severity=Severity.INFO, row_ids=[row_id], column_id=column.id, explanation="Text has external whitespace.", source="rule", proposal_id=proposal.id))
            if "email" in header and value and not EMAIL_RE.match(value):
                issues.append(Issue(id=f"issue_{uuid4().hex}", category=IssueCategory.SUSPICIOUS, severity=Severity.WARNING, row_ids=[row_id], column_id=column.id, explanation="Email format looks suspicious; deliverability was not checked.", source="rule"))
            if ("date" in header or "dob" in header) and DATE_RE.match(value):
                issues.append(Issue(id=f"issue_{uuid4().hex}", category=IssueCategory.SUSPICIOUS, severity=Severity.WARNING, row_ids=[row_id], column_id=column.id, explanation="Date is ambiguous without an explicit regional context; it was not converted.", source="rule"))

        if not protected:
            variants: dict[str, list[int]] = defaultdict(list)
            for index, value in enumerate(values):
                if value.strip():
                    variants[value.strip().casefold()].append(index)
            for indexes in variants.values():
                originals = {values[index] for index in indexes}
                if len(originals) > 1:
                    canonical = values[indexes[0]].strip()
                    for index in indexes[1:]:
                        if values[index] != canonical:
                            add_proposal(ProposalAction.SET_CELL, row_ids[index], column.id, values[index], canonical, "Normalize a case/spacing variant to the first observed spelling.")
                            issues.append(Issue(id=f"issue_{uuid4().hex}", category=IssueCategory.INCONSISTENT, severity=Severity.INFO, row_ids=[row_ids[index]], column_id=column.id, explanation="Value differs only by case or spacing from another observed category.", source="rule"))

    for issue in issues:
        if issue.proposal_id is None:
            matching = next((proposal for proposal in proposals if proposal.row_id in issue.row_ids and proposal.column_id == issue.column_id), None)
            if matching:
                issue.proposal_id = matching.id
    return Analysis(status="completed", rules_rows_checked=len(rows), issues=issues, proposals=proposals)


def apply_ai_findings(analysis: Analysis, findings: list[AIFinding]) -> None:
    """Convert validated provider findings into reviewable, never-accepted proposals."""
    for finding in findings:
        proposal_id: str | None = None
        if finding.action == ProposalAction.SET_CELL and finding.column_id is not None:
            duplicate = next((proposal for proposal in analysis.proposals if proposal.row_id == finding.row_id and proposal.column_id == finding.column_id and proposal.proposed_value == finding.proposed_value), None)
            if duplicate is None:
                proposal_id = f"prop_{uuid4().hex}"
                analysis.proposals.append(Proposal(id=proposal_id, action=ProposalAction.SET_CELL, row_id=finding.row_id, column_id=finding.column_id, original_value=finding.original_value, proposed_value=finding.proposed_value, reason=finding.explanation, source="ai", status=ProposalStatus.PENDING))
            else:
                proposal_id = duplicate.id
        analysis.issues.append(Issue(id=f"issue_{uuid4().hex}", category=finding.category, severity=Severity.WARNING, row_ids=[finding.row_id], column_id=finding.column_id, explanation=finding.explanation, source="ai", proposal_id=proposal_id))
