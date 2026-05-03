"use client";

import { useEffect, useState } from "react";
import { getKpis } from "@/lib/api";

type Kpis = {
  cashPosition: number | null;
  liquidityRatio: number | null;
  debtRatio: number | null;
  assetEfficiency: number | null;
  burnRate: number | null;
  workingCapital: number | null;
};

const EMPTY_KPIS: Kpis = {
  cashPosition: null,
  liquidityRatio: null,
  debtRatio: null,
  assetEfficiency: null,
  burnRate: null,
  workingCapital: null,
};

function hasValue(value: number | null | undefined): value is number {
  return value !== null && value !== undefined && Number.isFinite(value);
}

function currency(value: number | null) {
  if (!hasValue(value)) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function percent(value: number | null) {
  if (!hasValue(value)) return "-";
  return `${Math.round(value * 100)}%`;
}

function ratio(value: number | null) {
  if (!hasValue(value)) return "-";
  return value.toFixed(2);
}

function multiple(value: number | null) {
  if (!hasValue(value)) return "-";
  return `${value.toFixed(2)}x`;
}

function monthlyCurrency(value: number | null) {
  if (!hasValue(value)) return "-";
  return `${currency(value)}/month`;
}

export default function KPICards({ refreshKey = 0 }: { refreshKey?: number }) {
  const [data, setData] = useState<Kpis>(EMPTY_KPIS);

  useEffect(() => {
    async function loadKpis() {
      try {
        const result = await getKpis();
        setData({ ...EMPTY_KPIS, ...result });
      } catch (err) {
        console.error(err);
        setData(EMPTY_KPIS);
      }
    }

    loadKpis();
  }, [refreshKey]);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card title="Cash Position" value={currency(data.cashPosition)} />
      <Card title="Liquidity Ratio" value={ratio(data.liquidityRatio)} />
      <Card title="Debt Ratio" value={percent(data.debtRatio)} />
      <Card title="Asset Efficiency" value={multiple(data.assetEfficiency)} />
      <Card title="Burn Rate" value={monthlyCurrency(data.burnRate)} />
      <Card title="Working Capital" value={currency(data.workingCapital)} />
    </div>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="p-4 bg-white shadow rounded-2xl border">
      <p className="text-gray-500 text-sm">{title}</p>
      <h2 className="text-2xl font-bold mt-1">{value}</h2>
    </div>
  );
}