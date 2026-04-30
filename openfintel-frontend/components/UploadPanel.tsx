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

      alert(`Uploaded: ${data.uploaded} rows`);

      // reset file
      if (fileRef.current) fileRef.current.value = "";

      if (onUploadSuccess) onUploadSuccess();

    } catch (err: any) {
      console.error(err);
      alert(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        position: "relative",
        zIndex: 9999,
        background: "white",
        padding: "16px",
        borderRadius: "12px",
      }}
    >
      <input
        type="file"
        ref={fileRef}
        style={{
          display: "block",
          marginBottom: "10px",
          position: "relative",
          zIndex: 9999,
        }}
      />

      <button
        onClick={handleUpload}
        disabled={loading}
        style={{
          padding: "8px 16px",
          background: "#2563eb",
          color: "white",
          borderRadius: "8px",
        }}
      >
        {loading ? "Uploading..." : "Upload"}
      </button>
    </div>
  );
}