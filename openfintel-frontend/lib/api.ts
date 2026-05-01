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
  const res = await fetch(`${API_BASE}/api/dashboard`);
  return handle(res);
}

export async function getFiles() {
  const res = await fetch(`${API_BASE}/api/files`);
  return handle(res);
}

export async function getCoverage() {
  const res = await fetch(`${API_BASE}/api/coverage`);
  return handle(res);
}
