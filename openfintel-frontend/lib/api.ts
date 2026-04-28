// lib/api.ts

const BASE_URL = "https://openfintel.onrender.com";

// Generic fetch helper (better for debugging)
async function fetchAPI(endpoint: string) {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      cache: "no-store", // ensures fresh data
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

// Dashboard
export async function getDashboard() {
  return fetchAPI("/api/dashboard");
}

// Uploaded files
export async function getFiles() {
  return fetchAPI("/api/files");
}

// Coverage tracker
export async function getCoverage() {
  return fetchAPI("/api/coverage");
}
}