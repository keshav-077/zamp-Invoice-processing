"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getRun, submitReview, RunDetail } from "@/lib/api";
import { DecisionPanel } from "@/components/DecisionBadge";
import { POCandidateCards } from "@/components/EvidencePanels";

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;
  const [run, setRun] = useState<RunDetail | null>(null);
  const [selectedPo, setSelectedPo] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRun(runId).then(setRun).catch((e) => setError(e.message));
  }, [runId]);

  const handleSubmit = async (action: string, decision?: string) => {
    if (reason.trim().length < 5) {
      setError("Review reason is required (minimum 5 characters).");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await submitReview(runId, { action, po_id: selectedPo || undefined, decision, reason });
      router.push(`/runs/${runId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed");
      setSubmitting(false);
    }
  };

  if (!run) return <p className="text-muted">Loading review workspace...</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Review Workspace</h1>
        <p className="mt-1 text-muted">Resolve exception with mandatory audit reason</p>
      </div>

      <DecisionPanel decision={run.decision} reason={run.human_reason} />

      <POCandidateCards candidates={run.po_candidates} />

      <div className="card space-y-4 p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Resolution</h2>
        <div>
          <label className="text-sm font-medium text-slate-700">Select PO (if applicable)</label>
          <select
            value={selectedPo}
            onChange={(e) => setSelectedPo(e.target.value)}
            className="mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm"
          >
            <option value="">— Select PO —</option>
            {run.po_candidates.map((c) => (
              <option key={c.po_id as string} value={c.po_id as string}>{c.po_id as string} (score: {((c.total_score as number) * 100).toFixed(0)}%)</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700">Review reason *</label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm"
            placeholder="Explain your resolution decision..."
          />
        </div>
        {error && <p className="text-sm text-reject">{error}</p>}
        <div className="flex flex-wrap gap-3">
          {selectedPo && (
            <button onClick={() => handleSubmit("select_po")} disabled={submitting} className="btn-primary">
              Select PO & Approve
            </button>
          )}
          <button onClick={() => handleSubmit("override_decision", "REJECT")} disabled={submitting} className="btn-secondary">
            Override to REJECT
          </button>
        </div>
      </div>
    </div>
  );
}
