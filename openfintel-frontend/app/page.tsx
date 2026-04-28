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

        setData(dashboard);
        setFiles(fileList?.data || []);
        setCoverage(cov?.data || []);
      } catch (err) {
        console.error("Load error:", err);
        setData({ error: true });
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  // 🔄 Loading state
  if (loading) {
    return (
      <div>
        <Navbar />
        <div className="p-6">Loading dashboard...</div>
      </div>
    );
  }

  // ❌ No data / API failed
  if (!data || data.error) {
    return (
      <div>
        <Navbar />
        <div className="p-6 space-y-4">
          <h2 className="text-xl font-semibold">No data yet</h2>
          <p>Upload your financial CSV to get started.</p>
          <UploadPanel />
        </div>
      </div>
    );
  }

  // ✅ Main dashboard
  return (
    <div>
      <Navbar />

      <div className="p-6 space-y-6">
        {/* KPI Summary */}
        <KPICards data={data.summary} />

        {/* Upload */}
        <UploadPanel />

        {/* Uploaded files */}
        <FileTable files={files} />

        {/* Coverage */}
        <CoverageTracker data={coverage} />
      </div>
    </div>
  );
}