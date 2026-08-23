const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type RunSummary = {
  run_id: string;
  status: string;
  decision: string | null;
  vendor_name: string | null;
  invoice_number: string | null;
  total: number | null;
  currency: string | null;
  po_id: string | null;
  created_at: string;
  completed_at: string | null;
  processing_time_ms: number | null;
  reason_codes: string[];
};

export type RunDetail = RunSummary & {
  match_status: "MATCHED" | "POSSIBLE_MATCH" | "NO_MATCH" | null;
  match_result: {
    status: "MATCHED" | "POSSIBLE_MATCH" | "NO_MATCH";
    selected_po_id: string | null;
    top_candidate_id: string | null;
    top_score: number;
    runner_up_score: number;
    margin: number;
    matched_threshold: number;
    possible_threshold: number;
    minimum_margin: number;
    reason: string;
  } | null;
  current_stage: string | null;
  automated_decision: string | null;
  human_reason: string | null;
  file_name: string | null;
  page_count: number | null;
  error_message: string | null;
  events: Array<{ stage: string; status: string; message: string; data?: unknown; timestamp: string }>;
  extraction: Record<string, unknown> | null;
  model_metadata: Record<string, unknown> | null;
  normalized_invoice: Record<string, unknown> | null;
  vendor_resolution: Record<string, unknown> | null;
  po_candidates: Array<Record<string, unknown>>;
  validation_checks: Array<Record<string, unknown>>;
  duplicate_matches: Array<Record<string, unknown>>;
  audit_trail: Array<Record<string, unknown>>;
};

function formatApiError(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  return fallback;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { ...(options?.headers || {}) },
    });
  } catch {
    throw new Error(
      `Cannot reach the API at ${API_URL}. Start the backend with: cd apps/api && .venv\\Scripts\\Activate.ps1 && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
    );
  }
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => null);
    throw new Error(formatApiError(body, res.statusText || "Request failed"));
  }
  return res.json();
}

export async function getRuns(params?: Record<string, string>): Promise<RunSummary[]> {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return request(`/api/runs${qs}`);
}

export async function getRun(id: string): Promise<RunDetail> {
  return request(`/api/runs/${id}`);
}

export async function uploadInvoice(file: File): Promise<{ run_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return request("/api/runs", { method: "POST", body: form });
}

export async function getVendors(): Promise<Array<Record<string, unknown>>> {
  return request("/api/vendors");
}

export async function getPOs(query?: string): Promise<Array<Record<string, unknown>>> {
  const qs = query ? `?query=${encodeURIComponent(query)}` : "";
  return request(`/api/pos${qs}`);
}

export async function submitReview(runId: string, body: { action: string; po_id?: string; decision?: string; reason: string }) {
  return request(`/api/runs/${runId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function formatMoney(amount: unknown, currency = "USD") {
  if (amount == null || amount === "") return "Not found";
  const numericAmount =
    typeof amount === "number" ? amount : Number(String(amount));
  if (!Number.isFinite(numericAmount)) return "Not found";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(numericAmount);
}

export function decisionStyles(decision: string | null) {
  switch (decision) {
    case "APPROVE":
      return "bg-approve-bg text-approve border-approve/30";
    case "REVIEW":
      return "bg-review-bg text-review border-review/30";
    case "REJECT":
      return "bg-reject-bg text-reject border-reject/30";
    default:
      return "bg-slate-100 text-slate-600 border-slate-200";
  }
}
