const BASE_URL = "https://openfintel.onrender.com";

async function fetchAPI(endpoint: string) {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`API error: ${res.status}`);
    }

    return await res.json();
  } catch (error) {
    console.error(`Error fetching ${endpoint}:`, error);
    return null;
  }
}

export async function getDashboard() {
  return fetchAPI("/api/dashboard");
}

export async function getFiles() {
  return fetchAPI("/api/files");
}

export async function getCoverage() {
  return fetchAPI("/api/coverage");
}