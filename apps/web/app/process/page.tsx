"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, AlertCircle } from "lucide-react";
import { uploadInvoice } from "@/lib/api";

export default function ProcessPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.name.toLowerCase().endsWith(".pdf")) {
      setFile(f);
      setError(null);
    } else {
      setError("Only PDF files are accepted.");
    }
  }, []);

  const handleProcess = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await uploadInvoice(file);
      router.push(`/runs/${result.run_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Process Invoice</h1>
        <p className="mt-1 text-muted">Upload a vendor invoice PDF to start the workflow</p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`card flex flex-col items-center justify-center border-2 border-dashed p-12 transition-colors ${dragging ? "border-slate-900 bg-slate-50" : "border-surface-border"}`}
      >
        <Upload className="h-12 w-12 text-slate-400" />
        <p className="mt-4 text-sm font-medium text-slate-900">Drop PDF here or browse</p>
        <p className="mt-1 text-xs text-muted">Max 20MB · PDF only</p>
        <label className="btn-secondary mt-6 cursor-pointer">
          Browse files
          <input type="file" accept=".pdf" className="hidden" onChange={(e) => { setFile(e.target.files?.[0] || null); setError(null); }} />
        </label>
      </div>

      {file && (
        <div className="card flex items-center gap-4 p-4">
          <FileText className="h-8 w-8 text-slate-500" />
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
          <button onClick={handleProcess} disabled={loading} className="btn-primary disabled:opacity-50">
            {loading ? "Processing..." : "Process Invoice"}
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-reject/30 bg-reject-bg p-4 text-sm text-reject">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="card p-6">
        <h2 className="text-sm font-semibold text-slate-900">Demo fixtures</h2>
        <p className="mt-2 text-sm text-muted">Name your PDF file to match a scenario:</p>
        <ul className="mt-3 space-y-1 text-xs font-mono text-slate-600">
          <li>inv-001.pdf → Happy path (APPROVE)</li>
          <li>inv-002.pdf → No PO number (APPROVE)</li>
          <li>inv-003.pdf → Ambiguous POs (REVIEW)</li>
          <li>inv-004.pdf → Split invoice (APPROVE)</li>
          <li>inv-005.pdf → Over tolerance (REVIEW)</li>
          <li>inv-006.pdf → Duplicate (REJECT)</li>
          <li>inv-007.pdf → Wrong vendor (REVIEW)</li>
          <li>inv-008.pdf → Poor scan (REVIEW)</li>
        </ul>
      </div>
    </div>
  );
}
