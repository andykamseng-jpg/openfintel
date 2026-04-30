"use client";

import { useEffect, useState } from "react";
import UploadPanel from "@/components/UploadPanel";
import BASGraph from "@/components/BASGraph";
import MonthlyChart from "@/components/MonthlyChart";
import { getDashboard } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<any>(null);

  async function load() {
    const d = await getDashboard();
    setData(d);
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

    </div>
  );
}