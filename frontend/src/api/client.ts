const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");

export async function apiGet<T>(endpoint: string): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error("VITE_API_BASE_URL is not configured");
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return (await response.json()) as T;
}
