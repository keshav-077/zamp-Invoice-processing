import { formatMoney } from "@/lib/api";

type Check = {
  rule_id: string;
  name: string;
  result: string;
  message: string;
  invoice_value?: string;
  po_value?: string;
  blocking?: boolean;
};

export function ValidationChecks({ checks }: { checks: Check[] }) {
  if (!checks.length) return null;
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-surface-border px-6 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Validation Checks</h2>
      </div>
      <div className="divide-y divide-surface-border">
        {checks.map((c) => (
          <div key={c.rule_id + c.name} className="flex flex-wrap items-start justify-between gap-4 px-6 py-4">
            <div>
              <p className="text-sm font-medium text-slate-900">{c.name}</p>
              <p className="mt-1 text-sm text-muted">{c.message}</p>
              {(c.invoice_value || c.po_value) && (
                <p className="mt-1 text-xs text-slate-500">
                  Invoice: {c.invoice_value || "—"} · PO: {c.po_value || "—"}
                </p>
              )}
            </div>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase ${
                c.result === "pass"
                  ? "bg-approve-bg text-approve"
                  : c.result === "warn" || c.result === "skip"
                    ? "bg-review-bg text-review"
                    : "bg-reject-bg text-reject"
              }`}
            >
              {c.result}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ComparisonTable({
  invoice,
  po,
}: {
  invoice: Record<string, unknown> | null;
  po: Record<string, unknown> | null;
}) {
  if (!invoice) return null;
  const currency = (invoice.currency as string) || "USD";
  const rows = [
    { label: "Vendor", inv: invoice.vendor_name as string, po: po?.vendor_name as string },
    { label: "Invoice / PO #", inv: invoice.invoice_number as string, po: po?.po_id as string },
    { label: "Currency", inv: invoice.currency as string, po: po?.currency as string },
    { label: "Subtotal", inv: formatMoney(invoice.subtotal, currency), po: "—" },
    { label: "Tax", inv: formatMoney(invoice.tax, currency), po: "—" },
    { label: "Total", inv: formatMoney(invoice.total, currency), po: formatMoney(po?.remaining_value, (po?.currency as string) || currency) },
    { label: "PO Status", inv: "—", po: po?.status as string },
  ];
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-surface-border px-6 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Invoice vs PO Comparison</h2>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-surface-border bg-slate-50 text-left">
            <th className="px-6 py-3 font-medium text-muted">Field</th>
            <th className="px-6 py-3 font-medium text-muted">Invoice</th>
            <th className="px-6 py-3 font-medium text-muted">PO / Remaining</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-surface-border last:border-0">
              <td className="px-6 py-3 font-medium text-slate-700">{r.label}</td>
              <td className="px-6 py-3 tabular-nums">{r.inv || "—"}</td>
              <td className="px-6 py-3 tabular-nums">{r.po || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function InvoiceSummary({
  invoice,
}: {
  invoice: Record<string, unknown> | null;
}) {
  if (!invoice) return null;
  const currency = (invoice.currency as string) || "USD";
  const fields = [
    ["Vendor", invoice.vendor_name || "Not found"],
    ["Invoice number", invoice.invoice_number || "Not found"],
    ["Currency", invoice.currency || "Not found"],
    ["Subtotal", formatMoney(invoice.subtotal, currency)],
    ["Tax", formatMoney(invoice.tax, currency)],
    ["Total", formatMoney(invoice.total, currency)],
  ];
  return (
    <div className="card p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Invoice Details</h2>
      <dl className="mt-4 grid grid-cols-2 gap-4">
        {fields.map(([label, value]) => (
          <div key={String(label)}>
            <dt className="text-xs text-muted">{String(label)}</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">{String(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function MatchStatePanel({
  status,
  result,
}: {
  status: string | null;
  result: Record<string, unknown> | null;
}) {
  const matched = status === "MATCHED";
  const possible = status === "POSSIBLE_MATCH";
  return (
    <div className={`card border p-6 ${matched ? "border-approve/30" : "border-review/30"}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">PO Match Status</p>
      <h2 className={`mt-2 text-lg font-bold ${matched ? "text-approve" : "text-review"}`}>
        {matched
          ? `Matched PO ${result?.selected_po_id || ""}`
          : possible
            ? "Possible match — candidate not selected"
            : "No PO matched"}
      </h2>
      <p className="mt-2 text-sm text-muted">
        {(result?.reason as string) || "PO matching was not completed."}
      </p>
      {result && (
        <p className="mt-3 text-xs text-muted">
          Top score {((result.top_score as number) * 100).toFixed(0)}% · margin{" "}
          {((result.margin as number) * 100).toFixed(0)}% · confirmed threshold{" "}
          {((result.matched_threshold as number) * 100).toFixed(0)}%
        </p>
      )}
    </div>
  );
}

export function POCandidateCards({ candidates }: { candidates: Array<Record<string, unknown>> }) {
  if (!candidates.length) return null;
  return (
    <div className="card p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">PO Candidates</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {candidates.map((c) => (
          <div key={c.po_id as string} className={`rounded-lg border p-4 ${c.selected ? "border-slate-900 bg-slate-50" : "border-surface-border"}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-900">{c.po_id as string}</p>
                <p className="text-xs font-medium uppercase text-muted">
                  {c.selected ? "Matched PO" : "Candidate — not selected"}
                </p>
              </div>
              <span className="text-sm font-medium tabular-nums">Score: {((c.total_score as number) * 100).toFixed(0)}%</span>
            </div>
            {!(c.hard_constraints_pass as boolean) && (
              <p className="mt-2 text-xs text-reject">Hard constraint failures: {(c.hard_constraint_failures as string[])?.join(", ")}</p>
            )}
            <ul className="mt-3 space-y-1">
              {((c.signals as Array<Record<string, unknown>>) || []).map((s) => (
                <li key={s.signal as string} className="flex justify-between text-xs text-muted">
                  <span>{s.signal as string}</span>
                  <span>
                    {s.score == null
                      ? "Unavailable"
                      : `${((s.score as number) * 100).toFixed(0)}%`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
