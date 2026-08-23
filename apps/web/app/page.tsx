"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Upload, ArrowRight } from "lucide-react";
import { getRuns, RunSummary, formatMoney, decisionStyles } from "@/lib/api";
import clsx from "clsx";

export default function DashboardPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRuns()
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const stats = {
    total: runs.length,
    approved: runs.filter((r) => r.decision === "APPROVE").length,
    review: runs.filter((r) => r.decision === "REVIEW").length,
    rejected: runs.filter((r) => r.decision === "REJECT").length,
    avgTime: runs.filter((r) => r.processing_time_ms).reduce((a, r) => a + (r.processing_time_ms || 0), 0) / Math.max(runs.filter((r) => r.processing_time_ms).length, 1),
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-muted">Invoice processing runs and exception queue</p>
        </div>
        <Link href="/process" className="btn-primary">
          <Upload className="h-4 w-4" />
          Process Invoice
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { label: "Total Runs", value: stats.total },
          { label: "Approved", value: stats.approved, color: "text-approve" },
          { label: "Review", value: stats.review, color: "text-review" },
          { label: "Rejected", value: stats.rejected, color: "text-reject" },
          { label: "Avg Time", value: `${(stats.avgTime / 1000).toFixed(1)}s`, color: "text-slate-700" },
        ].map((s) => (
          <div key={s.label} className="card p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">{s.label}</p>
            <p className={clsx("mt-2 text-2xl font-bold tabular-nums", s.color)}>{s.value}</p>
          </div>
        ))}
      </div>

      <div className="card overflow-hidden">
        <div className="border-b border-surface-border px-6 py-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Recent Runs</h2>
        </div>
        {loading ? (
          <p className="p-6 text-sm text-muted">Loading runs...</p>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-muted">No runs yet. Upload an invoice to start processing.</p>
            <Link href="/process" className="btn-primary mt-4 inline-flex">
              Process Invoice <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border bg-slate-50 text-left">
                  <th className="px-6 py-3 font-medium text-muted">Time</th>
                  <th className="px-6 py-3 font-medium text-muted">Vendor</th>
                  <th className="px-6 py-3 font-medium text-muted">Invoice #</th>
                  <th className="px-6 py-3 font-medium text-muted text-right">Amount</th>
                  <th className="px-6 py-3 font-medium text-muted">PO</th>
                  <th className="px-6 py-3 font-medium text-muted">Decision</th>
                  <th className="px-6 py-3 font-medium text-muted"></th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.run_id} className="border-b border-surface-border hover:bg-slate-50">
                    <td className="px-6 py-4 text-muted">{new Date(run.created_at).toLocaleString()}</td>
                    <td className="px-6 py-4">{run.vendor_name || "—"}</td>
                    <td className="px-6 py-4 font-mono text-xs">{run.invoice_number || "—"}</td>
                    <td className="px-6 py-4 text-right tabular-nums">{formatMoney(run.total, run.currency || "USD")}</td>
                    <td className="px-6 py-4 font-mono text-xs">{run.po_id || "—"}</td>
                    <td className="px-6 py-4">
                      <span className={clsx("rounded-full border px-2 py-0.5 text-xs font-semibold", decisionStyles(run.decision))}>{run.decision || run.status}</span>
                    </td>
                    <td className="px-6 py-4">
                      <Link href={`/runs/${run.run_id}`} className="text-sm font-medium text-slate-900 hover:underline">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
