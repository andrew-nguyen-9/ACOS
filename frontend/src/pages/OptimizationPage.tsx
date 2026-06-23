import { useCallback, useEffect, useState } from "react";
import {
  listProposals, generateProposals, approveProposal, rejectProposal,
  applyProposal, revertProposal, listLogs, runLoop,
  type Proposal, type OptimizationLog,
} from "@/services/optimization";
import { ApiError } from "@/services/api";
import { PromptReview } from "@/components/optimization/PromptReview";

const CONFIDENCE_STYLE: Record<string, string> = {
  verified: "bg-green-500/15 text-green-300",
  strong_inference: "bg-blue-500/15 text-blue-300",
  weak_inference: "bg-amber-500/15 text-amber-300",
};
const RISK_STYLE: Record<string, string> = {
  low: "bg-green-500/15 text-green-300",
  medium: "bg-amber-500/15 text-amber-300",
  high: "bg-red-500/15 text-red-300",
};

export default function OptimizationPage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [logs, setLogs] = useState<OptimizationLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    const [p, l] = await Promise.all([listProposals(), listLogs()]);
    setProposals(p);
    setLogs(l);
  }, []);

  useEffect(() => { void reload().catch((e) => setError(String(e))); }, [reload]);

  const guard = async (fn: () => Promise<unknown>) => {
    setBusy(true); setError(null);
    try { await fn(); await reload(); }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  const active = proposals.filter((p) => p.status === "pending" || p.status === "approved");

  return (
    <div className="p-8 space-y-6 overflow-y-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-50">Optimization</h1>
          <p className="text-sm text-neutral-400">
            Review proposed improvements. Nothing is applied without your approval.
          </p>
        </div>
        <div className="flex gap-2">
          <button disabled={busy} onClick={() => void guard(generateProposals)}
            className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm disabled:opacity-50">
            Generate Recommendations
          </button>
          <button disabled={busy} onClick={() => void guard(runLoop)}
            className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white text-sm disabled:opacity-50">
            Run Learning Loop
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm p-3">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {active.length === 0 && (
          <p className="text-neutral-500 text-sm">No active proposals. Generate recommendations to begin.</p>
        )}
        {active.map((p) => (
          <div key={p.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-neutral-400">{p.target_engine}</span>
              <span className="text-sm font-medium text-neutral-100">{p.target_parameter}</span>
              <span className={`ml-auto text-xs px-2 py-0.5 rounded ${CONFIDENCE_STYLE[p.confidence_level]}`}>
                {p.confidence_level}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${RISK_STYLE[p.risk_level]}`}>
                risk: {p.risk_level}
              </span>
            </div>
            <div className="text-sm text-neutral-300">
              <span className="text-neutral-500">{p.current_value ?? "—"}</span>
              {" → "}
              <span className="text-neutral-100 font-medium">{p.proposed_value}</span>
            </div>
            <p className="text-sm text-neutral-300">{p.rationale}</p>
            <p className="text-xs text-neutral-400">Expected impact: {p.expected_impact}</p>
            <div className="flex gap-2 pt-1">
              {p.status === "pending" && (
                <>
                  <button disabled={busy} onClick={() => void guard(() => approveProposal(p.id))}
                    className="px-3 py-1.5 rounded-lg bg-green-600/80 hover:bg-green-600 text-white text-xs disabled:opacity-50">
                    Approve
                  </button>
                  <button disabled={busy} onClick={() => void guard(() => rejectProposal(p.id))}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs disabled:opacity-50">
                    Reject
                  </button>
                </>
              )}
              {p.status === "approved" && (
                <>
                  <button disabled={busy} onClick={() => void guard(() => applyProposal(p.id))}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs disabled:opacity-50">
                    Apply
                  </button>
                  <button disabled={busy} onClick={() => void guard(() => revertProposal(p.id))}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs disabled:opacity-50">
                    Revert
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      <div>
        <h2 className="text-sm font-semibold text-neutral-200 mb-2">Audit Log</h2>
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-white/[0.04] text-neutral-400">
              <tr>
                <th className="text-left px-3 py-2">Action</th>
                <th className="text-left px-3 py-2">Parameter</th>
                <th className="text-left px-3 py-2">Change</th>
                <th className="text-left px-3 py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-t border-white/5 text-neutral-300">
                  <td className="px-3 py-2">{l.action}</td>
                  <td className="px-3 py-2">{l.target_parameter}</td>
                  <td className="px-3 py-2">{l.old_value ?? "—"} → {l.new_value ?? "—"}</td>
                  <td className="px-3 py-2 text-neutral-500">{l.created_at}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={4} className="px-3 py-3 text-neutral-500">No changes recorded yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="pt-2 border-t border-white/10">
        <PromptReview />
      </div>
    </div>
  );
}
