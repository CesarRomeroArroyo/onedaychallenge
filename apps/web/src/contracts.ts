export type IssueCategory = "duplicate" | "inconsistent" | "missing" | "suspicious";
export type ProposalAction = "set_cell" | "exclude_row";
export type ProposalStatus = "pending" | "accepted" | "rejected";
export type Severity = "info" | "warning" | "error";

export interface Column { id: string; original_header: string; position: number; }
export interface Row { id: string; source_record_number: number; values: Record<string, string>; }
export interface Dataset { id: string; filename: string; created_at: string; expires_at: string; delimiter: string; columns: Column[]; row_count: number; revision: number; }
export interface Proposal { id: string; action: ProposalAction; row_id: string; column_id?: string; original_value: string; proposed_value?: string; reason: string; source: string; status: ProposalStatus; confidence?: number; }
export interface Issue { id: string; category: IssueCategory; severity: Severity; row_ids: string[]; column_id?: string; explanation: string; source: string; proposal_id?: string; }
export interface Analysis { status: string; rules_rows_checked: number; ai_rows_reviewed: number; ai_columns_reviewed: number; warnings: string[]; issues: Issue[]; proposals: Proposal[]; }
export interface ReviewRequest { expected_revision: number; decisions: { proposal_id: string; decision: ProposalStatus }[]; }
export interface ReviewSummary { revision: number; accepted: number; rejected: number; pending: number; excluded_rows: number; }
export interface UploadResponse { dataset: Dataset; preview: Row[]; }
export interface RowsResponse { items: Row[]; page: number; page_size: number; total: number; view: "original" | "effective"; }
