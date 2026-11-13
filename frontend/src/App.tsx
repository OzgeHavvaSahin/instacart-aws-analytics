
import { useEffect, useState } from "react";
import { apiGet } from "./api/client";
import type {
  ApiResponse,
  HealthData,
  SummaryData,
} from "./types/analytics";

function App() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function testConnection() {
      try {
        const [healthResult, summaryResult] = await Promise.all([
          apiGet<ApiResponse<HealthData>>("/api/health"),
          apiGet<ApiResponse<SummaryData>>("/api/summary"),
        ]);

        if (!healthResult.success || !summaryResult.success) {
          throw new Error("API returned success=false");
        }

        setHealth(healthResult.data);
        setSummary(summaryResult.data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Unknown error"
        );
      } finally {
        setLoading(false);
      }
    }

    testConnection();
  }, []);

  if (loading) {
    return <p>Connecting to AWS backend...</p>;
  }

  if (error) {
    return (
      <div>
        <h2>Connection failed</h2>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Instacart Analytics</h1>

      <h2>Backend Connection</h2>
      <p>Status: {health?.status}</p>
      <p>Service: {health?.service}</p>

      <h2>Athena Data</h2>
      <pre>{JSON.stringify(summary, null, 2)}</pre>
    </div>
  );
}

export default App;
