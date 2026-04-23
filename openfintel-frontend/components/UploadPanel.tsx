"use client";

import { useState } from "react";

export default function UploadPanel() {
  const [file, setFile] = useState<File | null>(null);

  const upload = async () => {
    if (!file) return alert("Select a file");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "income_statement");

    await fetch("https://openfintel.onrender.com/api/upload", {
      method: "POST",
      body: formData,
    });

    alert("Uploaded!");
    window.location.reload();
  };

  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="mb-2">Upload Document</h3>
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button
        onClick={upload}
        className="ml-2 px-3 py-1 bg-black text-white rounded"
      >
        Upload
      </button>
    </div>
  );
}