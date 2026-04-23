"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import KPICards from "@/components/KPICards";
import UploadPanel from "@/components/UploadPanel";
import FileTable from "@/components/FileTable";
import CoverageTracker from "@/components/CoverageTracker";
import { getDashboard, getFiles, getCoverage } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<any>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const dashboard = await getDashboard();
        const fileList = await getFiles();
        const cov = await getCoverage();

        setData(dashboard || {});
        setFiles(fileList?.data || []);
        setCoverage(cov?.data || []);
      } catch (err) {
        console.error("API error:", err);
        setData({ error: "Failed to load data" });
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  // 🔄 Loading state
  if (loading) {
    return <div className="p-6">Loading dashboard...</div>;
  }

  // ❌ Error or no data
  if (!data || data.error) {
    return (
      <div>
        <Navbar />
        <div className="p-6">
          <h2 className="text-xl font-semibold">No data yet</h2>
          <p className="text-gray-500 mt-2">
            Upload an income statement to get started.
          </p>
          <div className="mt-6">
            <UploadPanel />
          </div>
        </div>
      </div>
    );
  }

  // ✅ Normal UI
  return (
    <div>
      <Navbar />
      <div className="p-6 space-y-6">
        <KPICards data={data} />
        <UploadPanel />
        <FileTable files={files} />
        <CoverageTracker data={coverage} />
      </div>
    </div>
  );
}