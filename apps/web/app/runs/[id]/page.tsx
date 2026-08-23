"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getRun, RunDetail, getPOs } from "@/lib/api";
import { DecisionPanel } from "@/components/DecisionBadge";
import { StageTimeline } from "@/components/StageTimeline";
import {
  ValidationChecks,
  ComparisonTable,
  InvoiceSummary,
  MatchStatePanel,
  POCandidateCards,
} from "@/components/EvidencePanels";

const REASON_EXPLANATIONS: Record<string, string> = {
  DUPLICATE_EXACT: "Identical file content was processed previously.",
  DUPLICATE_PROBABLE: "Vendor, invoice number, amount, and currency match a prior invoice.",
  DUPLICATE_POSSIBLE: "Vendor, date, and amount resemble a prior invoice.",
  VENDOR_UNRESOLVED: "Vendor was not found in the approved vendor list.",
  NO_PO_MATCH: "No candidate exceeded the matching threshold.",
  AMBIGUOUS_PO_MATCH: "Candidate scores were too close or below the confirmed threshold.",
};

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [run, setRun] = useState<RunDetail | null>(null);
  const [po, setPo] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const data = await getRun(runId);
        if (!active) return;
        setRun(data);
        if (data.match_status === "MATCHED" && data.po_id) {
          const pos = await getPOs(data.po_id);
          setPo(pos.find((p: Record<string, unknown>) => p.po_id === data.po_id) || null);
        } else {
          setPo(null);
        }
        if (!["completed", "failed", "review"].includes(data.status)) {
          setTimeout(poll, 1500);
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Failed to load run");
      }
    };
    poll();
    return () => { active = false; };
  }, [runId]);

  if (error) return <p className="text-reject">{error}</p>;
  if (!run) return <p className="text-muted">Loading run...</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-mono text-muted">{run.run_id}</p>
          <h1 className="text-2xl font-bold text-slate-900">{run.file_name || "Invoice Run"}</h1>
          <p className="mt-1 text-sm text-muted">
            {run.processing_time_ms ? `Processed in ${(run.processing_time_ms / 1000).toFixed(1)}s` : "Processing..."}
          </p>
        </div>
        {run.decision === "REVIEW" && (
          <Link href={`/runs/${runId}/review`} className="btn-primary">
            Open Review Workspace
          </Link>
        )}
      </div>

      <DecisionPanel decision={run.decision} reason={run.human_reason} />

      {run.error_message && (
        <div className="rounded-lg border border-reject/30 bg-reject-bg p-4 text-sm text-reject">{run.error_message}</div>
      )}

      <MatchStatePanel
        status={run.match_status}
        result={run.match_result as Record<string, unknown> | null}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <StageTimeline events={run.events} />
        {run.match_status === "MATCHED" && po ? (
          <ComparisonTable invoice={run.normalized_invoice} po={po} />
        ) : (
          <InvoiceSummary invoice={run.normalized_invoice} />
        )}
      </div>

      <POCandidateCards candidates={run.po_candidates} />
      <ValidationChecks checks={run.validation_checks as never[]} />

      {run.duplicate_matches?.length > 0 && (
        <div className="card p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-reject">Duplicate Warnings</h2>
          <ul className="mt-3 space-y-2">
            {run.duplicate_matches.map((d, i) => (
              <li key={i} className="text-sm text-muted">
                <span className="mr-2 rounded bg-reject-bg px-2 py-0.5 text-xs font-semibold uppercase text-reject">
                  {String(d.match_type)}
                </span>
                {d.evidence as string}
              </li>
            ))}
          </ul>
        </div>
      )}

      {run.reason_codes?.length > 0 && (
        <div className="card p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Reason Codes</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {run.reason_codes.map((code) => (
              <div key={code} className="rounded-md bg-slate-100 px-3 py-2">
                <p className="font-mono text-xs">{code}</p>
                {REASON_EXPLANATIONS[code] && (
                  <p className="mt-1 text-xs text-muted">{REASON_EXPLANATIONS[code]}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <details className="card p-6">
        <summary className="cursor-pointer text-sm font-semibold text-muted">Technical Details</summary>
        <pre className="mt-4 overflow-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100">{JSON.stringify({ model_metadata: run.model_metadata, match_result: run.match_result, extraction: run.extraction, vendor_resolution: run.vendor_resolution, audit_trail: run.audit_trail }, null, 2)}</pre>
      </details>
    </div>
  );
}
