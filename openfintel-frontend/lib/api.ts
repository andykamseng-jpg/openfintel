const BASE = "https://openfintel.onrender.com";

export async function getDashboard() {
  const res = await fetch(`${BASE}/api/dashboard`);
  return res.json();
}

export async function getFiles() {
  const res = await fetch(`${BASE}/api/files`);
  return res.json();
}

export async function getCoverage() {
  const res = await fetch(`${BASE}/api/coverage`);
  return res.json();
}