"use client";

import { useState } from "react";
import { uploadFile } from "@/lib/api";

export default function UploadPanel() {
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e: any) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "income_statement");

    try {
      setLoading(true);
      await uploadFile(formData);

      alert(
        "Upload successful. Overlapping dates (if any) will be updated."
      );
    } catch (err) {
      alert("Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 bg-white shadow rounded-xl border">
      <h2 className="font-semibold mb-2">Upload Document</h2>

      <input
        type="file"
        onChange={handleUpload}
        className="block w-full text-sm"
      />

      {loading && <p className="text-sm mt-2">Uploading...</p>}
    </div>
  );
}