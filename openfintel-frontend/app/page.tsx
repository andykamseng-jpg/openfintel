"use client";

import { useCallback, useEffect, useState } from "react";
import UploadPanel from "@/components/UploadPanel";
import BASGraph from "@/components/BASGraph";
import MonthlyChart from "@/components/MonthlyChart";
import FileTable from "@/components/FileTable";
import CoverageTracker from "@/components/CoverageTracker";
import KPICards from "@/components/KPICards";

import { getDashboard, getFiles } from "@/lib/api";

type DashboardData = {
  graph?: unknown;
  monthly?: unknown[];
};

type FileRow = {
  filename: string;
  doc_type: string;
  rows_uploaded: number;
  rows_inserted: number;
  created_at?: string;
};

type CoverageRow = {
  doc_type: string;
  records: number;
};

function buildCoverageFromFiles(files: FileRow[]): CoverageRow[] {
  const totals = new Map<string, number>();

  for (const file of files) {
    totals.set(
      file.doc_type,
      (totals.get(file.doc_type) || 0) + (file.rows_uploaded || 0)
    );
  }

  return Array.from(totals.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([doc_type, records]) => ({ doc_type, records }));
}

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [files, setFiles] = useState<FileRow[]>([]);
  const [coverage, setCoverage] = useState<CoverageRow[]>([]);
  const [kpiRefreshKey, setKpiRefreshKey] = useState(0);

  const load = useCallback(async () => {
    try {
      const [d, f] = await Promise.all([
        getDashboard(),
        getFiles(),
      ]);
      const uploadRows = f.data || [];

      setData(d);
      setFiles(uploadRows);
      setCoverage(buildCoverageFromFiles(uploadRows));
      setKpiRefreshKey((key) => key + 1);
    } catch (err) {
      console.error("Load error:", err);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [load]);

  if (!data) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6 space-y-6">

      <KPICards refreshKey={kpiRefreshKey} />

      <BASGraph data={data.graph} />

      <MonthlyChart data={data.monthly || []} />

      <UploadPanel onUploadSuccess={load} />

      <FileTable files={files} />

      <CoverageTracker data={coverage} />

    </div>
  );
}
