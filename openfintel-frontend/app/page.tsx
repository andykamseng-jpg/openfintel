"use client";

import { useEffect, useState } from "react";

import Navbar from "@/components/Navbar";
import KPICards from "@/components/KPICards";
import BASGraph from "@/components/BASGraph";
import MonthlyChart from "@/components/MonthlyChart";
import FileTable from "@/components/FileTable";
import CoverageTracker from "@/components/CoverageTracker";
import UploadPanel from "@/components/UploadPanel";

import { getDashboard, getFiles, getCoverage } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<any>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setError(null);

      const [d, f, c] = await Promise.all([
        getDashboard(),
        getFiles(),
        getCoverage(),
      ]);

      setData(d);
      setFiles(f.data || []);
      setCoverage(c.data || []);
      setRefreshKey((k) => k + 1);

    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to load data");
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (error) {
    return <div className="p-6 text-red-600">❌ {error}</div>;
  }

  if (!data) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="min-h-screen flex flex-col">

      <Navbar />

      <div className="p-6 space-y-6">

        {/* KPI */}
        <KPICards refreshKey={refreshKey} />

        {/* BAS */}
        <BASGraph data={data.graph} />

        {/* Chart */}
        <MonthlyChart data={data.monthly} />

        {/* Upload */}
        <UploadPanel onUploadSuccess={load} />

        {/* Tables */}
        <div className="grid md:grid-cols-2 gap-6">
          <FileTable files={files} />
          <CoverageTracker data={coverage} />
        </div>

      </div>
    </div>
  );
}