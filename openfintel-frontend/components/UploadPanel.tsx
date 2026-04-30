"use client";

import { useState } from "react";

export default function UploadPanel({ onUploadSuccess }: any) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleUpload() {
    if (!file) {
      alert("Please select a file");
      return;
    }

    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "income_statement");

    try {
      const res = await fetch("https://openfintel.onrender.com/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      // ✅ IMPORTANT: check response
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      alert(`Upload successful: ${data.uploaded} rows`);

      if (onUploadSuccess) onUploadSuccess();

    } catch (err: any) {
      console.error("UPLOAD ERROR:", err);
      alert(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border p-4 rounded">
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />

      <button
        onClick={handleUpload}
        disabled={loading}
        className="ml-2 px-4 py-2 bg-blue-500 text-white rounded"
      >
        {loading ? "Uploading..." : "Upload"}
      </button>
    </div>
  );
}