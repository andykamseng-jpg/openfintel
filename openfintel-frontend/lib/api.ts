export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://openfintel.onrender.com";

async function handle(res: Response) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "API error");
  }
  return res.json();
}

export async function getDashboard() {
  const res = await fetch(`${API_BASE}/api/dashboard`, { cache: "no-store" });
  return handle(res);
}

export async function getFiles() {
  const res = await fetch(`${API_BASE}/api/files`, { cache: "no-store" });
  return handle(res);
}

export async function getCoverage() {
  const res = await fetch(`${API_BASE}/api/coverage`, { cache: "no-store" });
  return handle(res);
}

export async function getKpis() {
  const res = await fetch(`${API_BASE}/api/kpis`, { cache: "no-store" });
  const data = await handle(res);

  return {
    cashPosition: data.cash_position,
    liquidityRatio: data.liquidity_ratio,
    debtRatio: data.debt_ratio,
    assetEfficiency: data.asset_efficiency,
    burnRate: data.burn_rate,
    workingCapital: data.working_capital,
  };
}
