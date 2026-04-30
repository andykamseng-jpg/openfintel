"use client";

import { useEffect, useState } from "react";
import UploadPanel from "@/components/UploadPanel";
import BASGraph from "@/components/BASGraph";
import MonthlyChart from "@/components/MonthlyChart";
import FileTable from "@/components/FileTable";
import CoverageTracker from "@/components/CoverageTracker";

import { getDashboard, getFiles, getCoverage } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<any>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any[]>([]);

  async function load() {
    try {
      const [d, f, c] = await Promise.all([
        getDashboard(),
        getFiles(),
        getCoverage(),
      ]);

      setData(d);
      setFiles(f.data || []);
      setCoverage(c.data || []);
    } catch (err) {
      console.error("Load error:", err);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (!data) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6 space-y-6">

      <BASGraph data={data.graph} />

      <MonthlyChart data={data.monthly} />

      <UploadPanel onUploadSuccess={load} />

      <FileTable data={files} />

      <CoverageTracker data={coverage} />

    </div>
  );
}