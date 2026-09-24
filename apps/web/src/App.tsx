import { useEffect, useMemo, useState } from "react";
import { analyzeDataset, exportDataset, getHealth, getRows, reviewDataset, uploadCsv } from "./api";
import type { Analysis, Proposal, RowsResponse, UploadResponse } from "./contracts";
import { ReviewPanel } from "./ReviewPanel";

export function App() {
  const [health, setHealth] = useState("Checking API…");
  const [delimiter, setDelimiter] = useState("");
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [rows, setRows] = useState<RowsResponse | null>(null);
  const [view, setView] = useState<"original" | "effective">("original");
  const [safeExport, setSafeExport] = useState(false);
  const [editingProposalId, setEditingProposalId] = useState<string | null>(null);
  const [editedValue, setEditedValue] = useState("");

  useEffect(() => { getHealth().then(setHealth).catch(() => setHealth("API unavailable")); }, []);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setBusy(true); setError(""); setResult(null); setAnalysis(null);
    try { const uploaded = await uploadCsv(file, delimiter); setResult(uploaded); setRows({ items: uploaded.preview, page: 1, page_size: 5, total: uploaded.dataset.row_count, view: "original" }); } catch (err) { setError(err instanceof Error ? err.message : "Could not import CSV"); } finally { setBusy(false); }
  }

  async function handleSample() {
    setBusy(true); setError(""); setResult(null); setAnalysis(null);
    try {
      const response = await fetch("/customers-dirty.csv");
      if (!response.ok) throw new Error("Could not load sample CSV");
      await handleFile(new File([await response.blob()], "customers-dirty.csv", { type: "text/csv" }));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not load sample CSV"); setBusy(false); }
  }

  async function handleAnalyze() { if (!result) return; setBusy(true); setError(""); try { setAnalysis(await analyzeDataset(result.dataset.id)); setRows(await getRows(result.dataset.id, 1, view)); } catch (err) { setError(err instanceof Error ? err.message : "Could not analyze dataset"); } finally { setBusy(false); } }
  async function handleDecision(proposal: Proposal, decision: "accepted" | "rejected") { if (!result || !analysis) return; setBusy(true); setError(""); try { await reviewDataset(result.dataset.id, { expected_revision: result.dataset.revision, decisions: [{ proposal_id: proposal.id, decision }] }); const refreshed = await analyzeDataset(result.dataset.id); setAnalysis(refreshed); setResult({ ...result, dataset: { ...result.dataset, revision: result.dataset.revision + 1 } }); setRows(await getRows(result.dataset.id, 1, view)); } catch (err) { setError(err instanceof Error ? err.message : "Could not save review"); } finally { setBusy(false); } }
  function startEditing(proposal: Proposal) { if (proposal.status !== "pending" || proposal.proposed_value === undefined) return; setEditingProposalId(proposal.id); setEditedValue(proposal.proposed_value); }
  async function saveEditedSuggestion(proposal: Proposal) { if (!result || !analysis || !editedValue.trim()) return; setBusy(true); setError(""); try { await reviewDataset(result.dataset.id, { expected_revision: result.dataset.revision, decisions: [{ proposal_id: proposal.id, decision: "accepted", proposed_value: editedValue }] }); const refreshed = await analyzeDataset(result.dataset.id); setAnalysis(refreshed); setResult({ ...result, dataset: { ...result.dataset, revision: result.dataset.revision + 1 } }); setRows(await getRows(result.dataset.id, 1, view)); setEditingProposalId(null); } catch (err) { setError(err instanceof Error ? err.message : "Could not save edited suggestion"); } finally { setBusy(false); } }
  useEffect(() => { if (!result || !analysis) return; getRows(result.dataset.id, 1, view).then(setRows).catch(() => undefined); }, [view]);
  const counts = useMemo(() => analysis ? { pending: analysis.proposals.filter((item) => item.status === "pending").length, accepted: analysis.proposals.filter((item) => item.status === "accepted").length, rejected: analysis.proposals.filter((item) => item.status === "rejected").length } : null, [analysis]);
  const issueByCell = useMemo(() => {
    const cells = new Map<string, { category: string; severity: string; text: string; proposal?: Proposal }[]>();
    if (!analysis) return cells;
    for (const issue of analysis.issues) {
      for (const rowId of issue.row_ids) {
        if (!issue.column_id) continue;
        const key = `${rowId}:${issue.column_id}`;
        const items = cells.get(key) ?? [];
        items.push({ category: issue.category, severity: issue.severity, text: issue.explanation, proposal: issue.proposal_id ? analysis.proposals.find((item) => item.id === issue.proposal_id) : undefined });
        cells.set(key, items);
      }
    }
    return cells;
  }, [analysis]);

  return <main>
    <header><p className="eyebrow">CLEARCSV / DATA REVIEW WORKSPACE</p><h1>Clean data<br /><em>with confidence.</em></h1><p className="lede">Upload a CSV, preserve every value, and review evidence-backed suggestions before anything changes.</p></header>
    <section className="card" aria-labelledby="start-title">
      <h2 id="start-title">Start with your dataset</h2>
      <p>UTF-8 CSV · up to 2 MiB, 1,000 rows, and 30 columns. Values stay text, including leading zeros.</p>
       <div className="upload-actions"><label className="upload"><span>{busy ? "Working…" : "Choose CSV file"}</span><input type="file" accept=".csv,text/csv" disabled={busy} onChange={(event) => handleFile(event.target.files?.[0])} /></label><button className="secondary-button" disabled={busy} onClick={handleSample}>Try sample</button></div>
      <label className="field">Delimiter <select value={delimiter} onChange={(event) => setDelimiter(event.target.value)}><option value="">Auto-detect</option><option value=",">Comma (,)</option><option value=";">Semicolon (;)</option></select></label>
      <span className="status" role="status">{health}</span>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
    {result && <>
       <section className="card dataset-card" aria-labelledby="preview-title"><div className="dataset-header"><div><p className="section-kicker">Dataset ready</p><h2 id="preview-title">{result.dataset.filename}</h2><p>{result.dataset.row_count} rows · {result.dataset.columns.length} columns · delimiter “{result.dataset.delimiter}”</p></div><button className="primary-button" disabled={busy || Boolean(analysis)} onClick={handleAnalyze}>{analysis ? "Analysis complete" : busy ? "Analyzing…" : "Analyze data"}</button></div><p className="notice">A compact sample may be sent to configured AI provider. Sensitive-looking columns are excluded. Rules always check every row.</p>{analysis && <div className="table-legend"><span className="legend-finding">Finding</span><span className="legend-suggestion">Suggested change</span><span className="muted">Double-click suggested value to edit, then press Enter to apply.</span></div>}<div className="table-wrap"><table><thead><tr>{result.dataset.columns.map((column) => <th key={column.id}>{column.original_header || "(empty header)"}</th>)}</tr></thead><tbody>{(rows?.items ?? result.preview).map((row) => <tr key={row.id}>{result.dataset.columns.map((column) => { const cells = issueByCell.get(`${row.id}:${column.id}`) ?? []; return <td key={column.id} className={cells.length ? "flagged-cell" : undefined}>{row.values[column.id]}{cells.length > 0 && <div className="cell-notes">{cells.map((cell, index) => <details className={`cell-alert ${cell.proposal ? "suggestion" : "finding"}`} key={`${cell.category}-${index}`} open><summary><span className="alert-icon" aria-hidden="true">{cell.proposal ? "→" : "!"}</span><span><strong>{cell.proposal ? "Suggested change" : `Finding · ${cell.category}`}</strong>{cell.proposal && <small>{cell.proposal.proposed_value ?? cell.proposal.action}</small>}</span></summary><p>{cell.text}</p>{cell.proposal && <div className="alert-diff"><span>{cell.proposal.original_value || "(empty)"}</span><span aria-hidden="true">→</span>{editingProposalId === cell.proposal.id ? <input className="inline-edit" autoFocus value={editedValue} onChange={(event) => setEditedValue(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void saveEditedSuggestion(cell.proposal!); if (event.key === "Escape") setEditingProposalId(null); }} onBlur={() => setEditingProposalId(null)} aria-label="Edit suggested value" /> : <button className="suggested-value" onDoubleClick={() => startEditing(cell.proposal!)} title="Double-click to edit">{cell.proposal.proposed_value || "(empty)"}</button>}</div>}</details>)}</div>}</td>; })}</tr>)}</tbody></table></div></section>
      {analysis && <section className="analysis-layout"><div><div className="stats"><div><strong>{analysis.issues.length}</strong><span>findings</span></div><div><strong>{counts?.pending}</strong><span>pending</span></div><div><strong>{counts?.accepted}</strong><span>accepted</span></div><div><strong>{counts?.rejected}</strong><span>rejected</span></div></div><div className="coverage card"><p className="section-kicker">Coverage</p><p>Rules checked <strong>{analysis.rules_rows_checked}</strong> rows. AI reviewed <strong>{analysis.ai_rows_reviewed}</strong> rows and <strong>{analysis.ai_columns_reviewed}</strong> columns.</p>{analysis.warnings.map((warning) => <p className="warning" key={warning}>{warning}</p>)}</div><div className="card findings"><div className="panel-heading"><div><p className="section-kicker">Evidence log</p><h2>Findings without forced fixes</h2></div><div className="view-toggle"><button className={view === "original" ? "active" : ""} onClick={() => setView("original")}>Original</button><button className={view === "effective" ? "active" : ""} onClick={() => setView("effective")}>With accepted changes</button></div></div>{analysis.issues.filter((issue) => !issue.proposal_id).map((issue) => <div className="finding" key={issue.id}><span className={`tag ${issue.severity}`}>{issue.category}</span><p>{issue.explanation}</p></div>)}{analysis.issues.filter((issue) => !issue.proposal_id).length === 0 && <p className="muted">Every current finding has a reviewable proposal.</p>}</div></div><ReviewPanel analysis={analysis} onDecision={handleDecision} busy={busy} /></section>}
      {analysis && <section className="card export-card"><div><p className="section-kicker">Export</p><h2>Keep only decisions you accepted.</h2><p className="muted">Faithful CSV preserves values. Safe mode prefixes formula-like cells, including some negative values.</p></div><label className="check"><input type="checkbox" checked={safeExport} onChange={(event) => setSafeExport(event.target.checked)} /> Spreadsheet-safe export</label><a className="primary-button link-button" href={exportDataset(result.dataset.id, safeExport ? "spreadsheet_safe" : "faithful")}>Download CSV</a></section>}
    </>}
  </main>;
}
