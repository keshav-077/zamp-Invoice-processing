"use client";

import { useEffect, useState } from "react";
import { getVendors } from "@/lib/api";

export default function VendorsPage() {
  const [vendors, setVendors] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    getVendors().then(setVendors).catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Vendor Reference</h1>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-slate-50 text-left">
              <th className="px-6 py-3 font-medium text-muted">ID</th>
              <th className="px-6 py-3 font-medium text-muted">Legal Name</th>
              <th className="px-6 py-3 font-medium text-muted">Tax ID</th>
              <th className="px-6 py-3 font-medium text-muted">Currency</th>
              <th className="px-6 py-3 font-medium text-muted">Status</th>
            </tr>
          </thead>
          <tbody>
            {vendors.map((v) => (
              <tr key={v.vendor_id as string} className="border-b">
                <td className="px-6 py-3 font-mono text-xs">{v.vendor_id as string}</td>
                <td className="px-6 py-3">{v.legal_name as string}</td>
                <td className="px-6 py-3 font-mono text-xs">{v.tax_id as string}</td>
                <td className="px-6 py-3">{v.currency as string}</td>
                <td className="px-6 py-3">{v.status as string}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
