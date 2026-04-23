"use client";

import { useEffect, useState } from "react";
import { getFiles } from "@/lib/api";

export default function FileTable() {
  const [files, setFiles] = useState<any[]>([]);

  useEffect(() => {
    getFiles()
      .then((res) => setFiles(res.data))
      .catch(() => setFiles([]));
  }, []);

  return (
    <div className="p-4 bg-white shadow rounded-xl border">
      <h2 className="font-semibold mb-3">Recent Uploads</h2>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2">File Name</th>
            <th>Type</th>
            <th>Uploaded</th>
          </tr>
        </thead>

        <tbody>
          {files.length === 0 ? (
            <tr>
              <td colSpan={3} className="py-4 text-gray-500">
                No files uploaded yet
              </td>
            </tr>
          ) : (
            files.map((f, i) => (
              <tr key={i} className="border-b">
                <td className="py-2">{f.filename}</td>
                <td>{f.doc_type}</td>
                <td>
                  {new Date(f.upload_time).toLocaleString()}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}