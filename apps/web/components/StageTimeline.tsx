import { CheckCircle2, Circle, Loader2, AlertTriangle, XCircle } from "lucide-react";
import clsx from "clsx";

type Event = { stage: string; status: string; message: string; timestamp?: string };

const statusIcon = {
  success: CheckCircle2,
  running: Loader2,
  warning: AlertTriangle,
  error: XCircle,
  pending: Circle,
};

const statusColor = {
  success: "text-approve",
  running: "text-blue-600 animate-spin",
  warning: "text-review",
  error: "text-reject",
  pending: "text-slate-300",
};

const STAGE_LABELS: Record<string, string> = {
  uploaded: "Uploaded",
  rendering: "PDF Rendering",
  extracting: "Multimodal Extraction",
  verifying: "Field Verification",
  vendor_resolved: "Vendor Resolution",
  po_candidates: "PO Candidate Retrieval",
  po_match: "PO Matching",
  validating: "Validation Controls",
  duplicate_check: "Duplicate Check",
  decision: "Decision Engine",
  completed: "Completed",
  failed: "Failed",
};

export function StageTimeline({ events }: { events: Event[] }) {
  const stages = events.length ? events : [];
  return (
    <div className="card p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Processing Timeline</h2>
      <ol className="mt-6 space-y-0">
        {stages.map((event, i) => {
          const Icon = statusIcon[event.status as keyof typeof statusIcon] || Circle;
          const isLast = i === stages.length - 1;
          return (
            <li key={`${event.stage}-${i}`} className="relative flex gap-4 pb-6">
              {!isLast && <span className="absolute left-[11px] top-6 h-full w-px bg-surface-border" />}
              <Icon className={clsx("relative z-10 h-6 w-6 shrink-0", statusColor[event.status as keyof typeof statusColor] || "text-slate-300")} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-900">{STAGE_LABELS[event.stage] || event.stage}</p>
                <p className="mt-0.5 text-sm text-muted">{event.message}</p>
                {event.timestamp && <p className="mt-1 text-xs text-slate-400">{new Date(event.timestamp).toLocaleTimeString()}</p>}
              </div>
            </li>
          );
        })}
        {stages.length === 0 && <p className="text-sm text-muted">Waiting for processing to begin...</p>}
      </ol>
    </div>
  );
}
