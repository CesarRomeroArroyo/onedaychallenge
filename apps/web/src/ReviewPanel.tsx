import { useState } from "react";
import type { Analysis, IssueCategory, Proposal, ProposalStatus } from "./contracts";

type Props = { analysis: Analysis; onDecision: (proposal: Proposal, decision: Exclude<ProposalStatus, "pending">) => void; busy: boolean };

export function ReviewPanel({ analysis, onDecision, busy }: Props) {
  const [category, setCategory] = useState<"all" | IssueCategory>("all");
  const [source, setSource] = useState("all");
  const [status, setStatus] = useState<"all" | ProposalStatus>("all");
  const proposals = analysis.proposals.filter((proposal) => {
    const issue = analysis.issues.find((item) => item.proposal_id === proposal.id);
    return (category === "all" || issue?.category === category) && (source === "all" || proposal.source.toLowerCase() === source) && (status === "all" || proposal.status === status);
  });
  return <aside className="review-panel" aria-labelledby="proposals-title">
    <div className="panel-heading"><div><p className="section-kicker">Human review</p><h2 id="proposals-title">Suggested changes</h2></div><span className="count-badge">{proposals.filter((item) => item.status === "pending").length} pending</span></div>
    <div className="filters" aria-label="Filter proposals"><select aria-label="Filter category" value={category} onChange={(event) => setCategory(event.target.value as "all" | IssueCategory)}><option value="all">All categories</option><option value="duplicate">Duplicate</option><option value="inconsistent">Inconsistent</option><option value="missing">Missing</option><option value="suspicious">Suspicious</option></select><select aria-label="Filter source" value={source} onChange={(event) => setSource(event.target.value)}><option value="all">All sources</option><option value="rule">Rules</option><option value="ai">AI</option></select><select aria-label="Filter status" value={status} onChange={(event) => setStatus(event.target.value as "all" | ProposalStatus)}><option value="all">All statuses</option><option value="pending">Pending</option><option value="accepted">Accepted</option><option value="rejected">Rejected</option></select></div>
    {proposals.length === 0 && <p className="muted">No corrections match filters. Findings without a safe proposal stay visible in the analysis.</p>}
    <div className="proposal-list">{proposals.map((proposal) => <article className={`proposal ${proposal.status}`} key={proposal.id}>
      <div className="proposal-top"><span className={`tag ${proposal.source.toLowerCase()}`}>{proposal.source}</span><span className="proposal-status">{proposal.status}</span></div>
      <strong>{proposal.action === "exclude_row" ? "Exclude duplicate row" : "Update cell"}</strong>
      <p className="change"><code>{proposal.original_value || "(empty)"}</code>{proposal.proposed_value !== undefined && <><span aria-hidden="true">→</span><code className="suggested">{proposal.proposed_value}</code></>}</p>
      <p className="muted">{proposal.reason}</p>
      {proposal.status === "pending" && <div className="proposal-actions"><button disabled={busy} onClick={() => onDecision(proposal, "accepted")}>Accept</button><button className="quiet-button" disabled={busy} onClick={() => onDecision(proposal, "rejected")}>Reject</button></div>}
    </article>)}</div>
  </aside>;
}
