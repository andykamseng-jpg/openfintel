const BASE_URL = "https://openfintel.onrender.com";

async function fetchAPI(endpoint: string) {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      cache: "no-store",
    });

    if (!res.ok) {
      console.error("API error:", res.status);
      return null;
    }

    return await res.json();
  } catch (err) {
    console.error("Fetch failed:", err);
    return null;
  }
}

export const getDashboard = () => fetchAPI("/api/dashboard");
export const getFiles = () => fetchAPI("/api/files");
export const getCoverage = () => fetchAPI("/api/coverage");