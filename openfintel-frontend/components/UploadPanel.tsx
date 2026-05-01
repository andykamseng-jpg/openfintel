"use client";

import { useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

type UploadPanelProps = {
  onUploadSuccess?: () => void | Promise<void>;
};

type UploadResponse = {
  uploaded: number;
  inserted: number;
  detail?: string;
};

export default function UploadPanel({ onUploadSuccess }: UploadPanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);

  function openFilePicker() {
    fileRef.current?.click();
  }

  async function handleUpload(file: File) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      alert("Please upload a CSV file.");
      if (fileRef.current) fileRef.current.value = "";
      return;
    }

    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "income_statement");

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
      });

      const text = await res.text();
      const contentType = res.headers.get("content-type") || "";

      let data: UploadResponse;

      if (!contentType.includes("application/json")) {
        console.error("Upload returned non-JSON response:", text);
        throw new Error(
          text.trim() || "Upload failed because the server returned an invalid response."
        );
      }

      try {
        data = JSON.parse(text) as UploadResponse;
      } catch {
        console.error("Upload returned malformed JSON:", text);
        throw new Error("Upload failed because the server returned malformed JSON.");
      }

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      const duplicates = data.uploaded - data.inserted;

      alert(
        `Upload complete\n\nUploaded: ${data.uploaded}\nInserted: ${data.inserted}\nDuplicates skipped: ${duplicates}`
      );

      await onUploadSuccess?.();
    } catch (err: unknown) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className="border p-4 rounded">
      <input
        type="file"
        accept=".csv,text/csv"
        ref={fileRef}
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleUpload(file);
        }}
      />

      <button
        onClick={openFilePicker}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        {loading ? "Uploading..." : "Upload File"}
      </button>
    </div>
  );
}
