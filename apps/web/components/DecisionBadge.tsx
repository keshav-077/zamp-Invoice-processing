import clsx from "clsx";
import { decisionStyles } from "@/lib/api";

export function DecisionBadge({ decision }: { decision: string | null }) {
  return (
    <span className={clsx("inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide", decisionStyles(decision))}>
      {decision || "PENDING"}
    </span>
  );
}

export function DecisionPanel({ decision, reason }: { decision: string | null; reason?: string | null }) {
  return (
    <div className={clsx("card p-6", decisionStyles(decision))}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider opacity-70">Decision</p>
          <p className="mt-1 text-3xl font-bold">{decision || "Processing..."}</p>
          {reason && <p className="mt-2 max-w-2xl text-sm leading-relaxed opacity-90">{reason}</p>}
        </div>
        <DecisionBadge decision={decision} />
      </div>
    </div>
  );
}
