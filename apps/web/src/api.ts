import type { Analysis, ReviewRequest, ReviewSummary, RowsResponse, UploadResponse } from "./contracts";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function uploadCsv(file: File, delimiter: string): Promise<UploadResponse> {
  const body = new FormData();
  body.append("file", file);
  if (delimiter) body.append("delimiter", delimiter);
  const response = await fetch(`${apiBase}/api/datasets`, { method: "POST", body });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail?.message ?? "Could not import CSV");
  return payload as UploadResponse;
}

export async function getHealth(): Promise<string> {
  const response = await fetch(`${apiBase}/api/health`);
  if (!response.ok) throw new Error("API unavailable");
  const data = (await response.json()) as { status: string };
  return `API ${data.status}`;
}

async function jsonRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${url}`, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail?.message ?? "Request failed");
  return payload as T;
}

export function analyzeDataset(id: string): Promise<Analysis> {
  return jsonRequest<Analysis>(`/api/datasets/${id}/analyze`, { method: "POST" });
}

export function getAnalysis(id: string): Promise<Analysis> {
  return jsonRequest<Analysis>(`/api/datasets/${id}/analysis`);
}

export function getRows(id: string, page: number, view: "original" | "effective"): Promise<RowsResponse> {
  return jsonRequest<RowsResponse>(`/api/datasets/${id}/rows?page=${page}&page_size=25&view=${view}`);
}

export function reviewDataset(id: string, request: ReviewRequest): Promise<ReviewSummary> {
  return jsonRequest<ReviewSummary>(`/api/datasets/${id}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) });
}

export function exportDataset(id: string, mode: "faithful" | "spreadsheet_safe"): string {
  return `${apiBase}/api/datasets/${id}/export?mode=${mode}`;
}
