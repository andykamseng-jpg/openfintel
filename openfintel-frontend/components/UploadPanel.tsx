"use client";

import { useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

export default function UploadPanel({ onUploadSuccess }: any) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);

  function openFilePicker() {
    fileRef.current?.click();
  }

  async function handleUpload(file: File) {
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "income_statement");

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      alert(`Uploaded: ${data.uploaded}, Inserted: ${data.inserted}`);

      await onUploadSuccess?.();

    } catch (err) {
      console.error(err);
      alert("Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white p-4 rounded-2xl shadow border">
      <button
        onClick={openFilePicker}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        {loading ? "Uploading..." : "Upload File"}
      </button>

      <input
        type="file"
        ref={fileRef}
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleUpload(file);
        }}
      />
    </div>
  );
}