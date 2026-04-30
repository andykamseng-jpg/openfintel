"use client";

import { useState, useRef } from "react";

export default function UploadPanel({ onUploadSuccess }: any) {
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

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
      const res = await fetch(
        "https://openfintel.onrender.com/api/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      alert("Upload successful");

      // reset input
      if (fileRef.current) {
        fileRef.current.value = "";
      }

      setFileName("");

      if (onUploadSuccess) {
        onUploadSuccess();
      }

    } catch (err: any) {
      console.error("UPLOAD ERROR:", err);
      alert(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border p-4 rounded space-y-3">

      <input
        type="file"
        ref={fileRef}
        onChange={(e) =>
          setFileName(e.target.files?.[0]?.name || "")
        }
        className="block"
      />

      {fileName && (
        <p className="text-sm text-gray-600">
          Selected: {fileName}
        </p>
      )}

      <button
        onClick={handleUpload}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded"
      >
        {loading ? "Uploading..." : "Upload"}
      </button>

    </div>
  );
}