"use client";

import { useRef, useState } from "react";

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
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      // ✅ Always read raw response first
      const text = await res.text();

      let data;

      try {
        data = JSON.parse(text);
      } catch {
        console.error("RAW RESPONSE:", text);
        throw new Error("Server returned invalid response");
      }

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      // ✅ USE the backend result
      const duplicates = data.uploaded - data.inserted;

      alert(
        `Upload complete\n\nUploaded: ${data.uploaded}\nInserted: ${data.inserted}\nDuplicates skipped: ${duplicates}`
      );

      if (onUploadSuccess) onUploadSuccess();

    } catch (err: any) {
      console.error(err);
      alert(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border p-4 rounded">

      <input
        type="file"
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