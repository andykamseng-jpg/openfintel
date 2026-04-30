"use client";

import { useRef, useState } from "react";

export default function UploadPanel({ onUploadSuccess }: any) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];

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

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      alert(`Upload successful: ${data.uploaded} rows`);

      // reset input
      if (fileRef.current) fileRef.current.value = "";

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
      <input type="file" ref={fileRef} />

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