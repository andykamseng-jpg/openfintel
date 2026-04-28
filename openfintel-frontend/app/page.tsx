"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import KPICards from "@/components/KPICards";
import UploadPanel from "@/components/UploadPanel";
import FileTable from "@/components/FileTable";
import CoverageTracker from "@/components/CoverageTracker";
import MonthlyChart from "@/components/MonthlyChart";

import { getDashboard, getFiles, getCoverage } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<any>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const dashboard = await getDashboard();
      const fileList = await getFiles();
      const cov = await getCoverage();

      setData(dashboard || null);
      setFiles(fileList?.data || []);
      setCoverage(cov?.data || []);
      setLoading(false);
    }

    load();
  }, []);

  if (loading) {
    return <div className="p-6">Loading...</div>;
  }

  if (!data) {
    return (
      <div>
        <Navbar />
        <div className="p-6 space-y-4">
          <h2>No data yet</h2>
          <UploadPanel />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Navbar />

      <div className="p-6 space-y-6">

        {/* KPI */}
        <KPICards data={data.summary} />

        {/* 📈 Monthly Chart */}
        <MonthlyChart data={data.monthly} />

        {/* Upload */}
        <UploadPanel />

        {/* Files */}
        <FileTable files={files} />

        {/* Coverage */}
        <CoverageTracker data={coverage} />

      </div>
    </div>
  );
}