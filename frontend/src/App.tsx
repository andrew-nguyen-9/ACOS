import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000/api/v1";

interface HealthResponse {
  status: string;
  db: string;
  version: string;
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setError("Backend unreachable"));
  }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col items-center justify-center gap-4">
      <h1 className="text-3xl font-bold tracking-tight">ACOS</h1>
      <p className="text-gray-400 text-sm">AI Career Operating System</p>

      {error && (
        <div className="mt-4 px-4 py-2 bg-red-900/40 border border-red-700 rounded text-red-300 text-sm">
          {error}
        </div>
      )}

      {health && (
        <div className="mt-4 px-6 py-4 bg-gray-900 border border-gray-800 rounded-lg text-sm space-y-1">
          <div>
            Status:{" "}
            <span className="text-green-400 font-mono">{health.status}</span>
          </div>
          <div>
            DB:{" "}
            <span className="text-green-400 font-mono">{health.db}</span>
          </div>
          <div>
            Version:{" "}
            <span className="text-blue-400 font-mono">{health.version}</span>
          </div>
        </div>
      )}
    </div>
  );
}
