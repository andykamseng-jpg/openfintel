const BASE_URL = "https://openfintel.onrender.com";

export async function getDashboard() {
  const res = await fetch(`${BASE_URL}/api/dashboard`);
  return res.json();
}

export async function getFiles() {
  const res = await fetch(`${BASE_URL}/api/files`);
  return res.json();
}

export async function getCoverage() {
  const res = await fetch(`${BASE_URL}/api/coverage`);
  return res.json();
}