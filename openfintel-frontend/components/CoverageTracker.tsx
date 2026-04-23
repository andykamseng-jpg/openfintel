"use client";

import { useEffect, useState } from "react";
import { getCoverage } from "@/lib/api";

export default function CoverageTracker() {
  const [coverage, setCoverage] = useState<any[]>([]);

  useEffect(() => {
    getCoverage()
      .then((res) => setCoverage(res.data))
      .catch(() => setCoverage([]));
  }, []);

  return (
    <div className="p-4 bg-white shadow rounded-xl border">
      <h2 className="font-semibold mb-3">Data Coverage</h2>

      <div className="flex flex-wrap gap-2">
        {coverage.length === 0 ? (
          <p className="text-gray-500 text-sm">
            No data coverage available yet
          </p>
        ) : (
          coverage.map((c, i) => (
            <span
              key={i}
              className={`px-2 py-1 text-xs rounded ${
                c.exists ? "bg-green-200" : "bg-red-200"
              }`}
            >
              {c.date}
            </span>
          ))
        )}
      </div>
    </div>
  );
}