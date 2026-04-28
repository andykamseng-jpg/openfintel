const BASE_URL = "https://openfintel.onrender.com";

async function fetchAPI(endpoint: string) {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      cache: "no-store",
    });

    if (!res.ok) throw new Error("API error");

    return await res.json();
  } catch (err) {
    console.error(err);
    return null;
  }
}

export const getDashboard = () => fetchAPI("/api/dashboard");
export const getFiles = () => fetchAPI("/api/files");
export const getCoverage = () => fetchAPI("/api/coverage");