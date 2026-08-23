"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileText, ImageIcon, AlertCircle } from "lucide-react";
import { uploadInvoice } from "@/lib/api";

const ACCEPTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"];
const ACCEPT_ATTR = ACCEPTED_EXTENSIONS.join(",");

function isAcceptedFile(file: File): boolean {
  return ACCEPTED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
}

function isImageFile(file: File): boolean {
  const lower = file.name.toLowerCase();
  return [".png", ".jpg", ".jpeg", ".webp"].some((ext) => lower.endsWith(ext));
}

export default function ProcessPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = useCallback((f: File | null | undefined) => {
    if (!f) return;
    if (isAcceptedFile(f)) {
      setFile(f);
      setError(null);
    } else {
      setError("Only PDF, PNG, JPG, and WebP files are accepted.");
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      handleFileSelect(e.dataTransfer.files[0]);
    },
    [handleFileSelect],
  );

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
        <p className="mt-1 text-muted">Upload a vendor invoice PDF or image to start the workflow</p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`card flex flex-col items-center justify-center border-2 border-dashed p-12 transition-colors ${dragging ? "border-slate-900 bg-slate-50" : "border-surface-border"}`}
      >
        <Upload className="h-12 w-12 text-slate-400" />
        <p className="mt-4 text-sm font-medium text-slate-900">Drop PDF or image here or browse</p>
        <p className="mt-1 text-xs text-muted">Max 20MB · PDF, PNG, JPG, WebP</p>
        <label className="btn-secondary mt-6 cursor-pointer">
          Browse files
          <input
            type="file"
            accept={ACCEPT_ATTR}
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files?.[0])}
          />
        </label>
      </div>

      {file && (
        <div className="card flex items-center gap-4 p-4">
          {isImageFile(file) ? (
            <ImageIcon className="h-8 w-8 text-slate-500" />
          ) : (
            <FileText className="h-8 w-8 text-slate-500" />
          )}
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
    </div>
  );
}
