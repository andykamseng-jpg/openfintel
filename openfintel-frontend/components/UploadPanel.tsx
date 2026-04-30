"use client";

import { useState } from "react";

export default function UploadPanel({ onUploadSuccess }: any) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleUpload() {
    if (!file) return;

    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    // ✅ REQUIRED FIX
    formData.append("doc_type", "income_statement");

    try {
      await fetch("https://openfintel.onrender.com/api/upload", {
        method: "POST",
        body: formData,
      });

      alert("Upload successful");

      if (onUploadSuccess) onUploadSuccess();

    } catch (err) {
      console.error(err);
      alert("Upload failed");
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