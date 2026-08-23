"use client";

import { useEffect, useState } from "react";
import { getPOs, formatMoney } from "@/lib/api";

export default function POsPage() {
  const [pos, setPos] = useState<Array<Record<string, unknown>>>([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    getPOs(query || undefined).then(setPos).catch(console.error);
  }, [query]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Purchase Orders</h1>
        <input
          type="search"
          placeholder="Search PO..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="rounded-lg border border-surface-border px-3 py-2 text-sm"
        />
      </div>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-slate-50 text-left">
              <th className="px-6 py-3 font-medium text-muted">PO #</th>
              <th className="px-6 py-3 font-medium text-muted">Vendor</th>
              <th className="px-6 py-3 font-medium text-muted">Status</th>
              <th className="px-6 py-3 font-medium text-muted text-right">Total</th>
              <th className="px-6 py-3 font-medium text-muted text-right">Remaining</th>
            </tr>
          </thead>
          <tbody>
            {pos.map((po) => (
              <tr key={po.po_id as string} className="border-b">
                <td className="px-6 py-3 font-mono text-xs">{po.po_id as string}</td>
                <td className="px-6 py-3">{po.vendor_name as string}</td>
                <td className="px-6 py-3">{po.status as string}</td>
                <td className="px-6 py-3 text-right tabular-nums">{formatMoney(po.total_value, po.currency as string)}</td>
                <td className="px-6 py-3 text-right tabular-nums">{formatMoney(po.remaining_value, po.currency as string)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
