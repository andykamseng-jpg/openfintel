"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import KPICards from "@/components/KPICards";
import UploadPanel from "@/components/UploadPanel";
import FileTable from "@/components/FileTable";
import CoverageTracker from "@/components/CoverageTracker";
import { getDashboard, getFiles, getCoverage } from "@/lib/api";
import MonthlyChart from "@/components/MonthlyChart";

export default function Home() {
  const [data, setData] = useState<any>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const d = await getDashboard();
      const f = await getFiles();
      const c = await getCoverage();

      setData(d);
      setFiles(f?.data || []);
      setCoverage(c?.data || []);
      setLoading(false);
    }

    load();
  }, []);

  if (loading) return <div className="p-6">Loading...</div>;

  if (!data) return <UploadPanel />;

  return (
    <div>
      <Navbar />
      <div className="p-6 space-y-6">
        <KPICards data={data.summary} />
        <UploadPanel />
        <FileTable files={files} />
        <CoverageTracker data={coverage} />
      </div>
    </div>
  );
}