import { useCallback, useEffect, useState } from "react";
import { GitBranch } from "lucide-react";
import { ApiError } from "@/services/api";
import { flywheelService } from "@/services/flywheel";
import type { PromptVersionsResponse } from "@/types/flywheel";

/**
 * Phase 13.4 — human-in-the-loop review queue for evolved prompts.
 *
 * This is the destination 13.6's automation feeds. It surfaces the read side
 * (GET /flywheel/prompt/versions) as a candidate lineage, then drives the four
 * mutation POSTs. The hard rules (ADR-010, mirrored from the server gate):
 *  - Promotion is a DELIBERATE human act — disabled until an approver is named;
 *    `approved_by` is never auto-filled.
 *  - The active (`is_active`) incumbent is clearly marked LIVE; candidates are not.
 *  - Each candidate shows its rationale + signal links (no unexplained proposal).
 *  - Rollback is one click and visibly restores the prior active version.
 *  - Promote and rollback both confirm before mutating (destructive).
 *
 * ponytail: the read route is per-prompt, and no list-all-prompts route exists,
 * so the reviewer names the prompt. Defaults to the canonical one.
 */
const DEFAULT_PROMPT = "resume/extract_keywords";

export function PromptReview() {
  const [promptName, setPromptName] = useState(DEFAULT_PROMPT);
  const [draftName, setDraftName] = useState(DEFAULT_PROMPT);
  const [approver, setApprover] = useState("");
  const [data, setData] = useState<PromptVersionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (name: string) => {
    setData(await flywheelService.getPromptVersions(name));
  }, []);

  useEffect(() => {
    void load(promptName).catch((e) => setError(String(e)));
  }, [load, promptName]);

  const guard = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load(promptName);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const canApprove = approver.trim().length > 0;

  const promote = (version: string) => {
    if (!canApprove) return; // belt-and-braces; the button is also disabled
    if (!window.confirm(`Promote ${promptName} ${version} to LIVE? This changes the active prompt.`))
      return;
    void guard(() =>
      flywheelService.promotePrompt({ prompt_name: promptName, version, approved_by: approver.trim() }),
    );
  };

  const rollback = () => {
    if (!window.confirm(`Roll back ${promptName} to its prior active version?`)) return;
    void guard(() =>
      // approver is optional for rollback (server defaults "user"); send it when named.
      flywheelService.rollbackPrompt({
        prompt_name: promptName,
        approved_by: approver.trim() || undefined,
      }),
    );
  };

  const active = data?.versions.find((v) => v.is_active);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <GitBranch className="size-4 text-indigo-400" />
        <h2 className="text-sm font-semibold text-neutral-200">Prompt Evolution Review</h2>
      </div>
      <p className="text-xs text-neutral-400">
        Candidate prompts evolved from success signals. Nothing goes live without your explicit approval.
      </p>

      {/* Which prompt to review (per-prompt read route). */}
      <div className="flex items-center gap-2">
        <input
          data-testid="prompt-name-input"
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          className="flex-1 rounded-lg bg-white/[0.04] border border-white/10 px-3 py-1.5 text-sm text-neutral-100"
          placeholder="prompt name (e.g. resume/extract_keywords)"
        />
        <button
          disabled={busy}
          onClick={() => setPromptName(draftName.trim())}
          className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-sm disabled:opacity-50"
        >
          Load
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm p-3">
          {error}
        </div>
      )}

      {/* Approver: promotion is a deliberate human act — never auto-filled. */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-neutral-400" htmlFor="approver">
          Approving as
        </label>
        <input
          id="approver"
          data-testid="approver-input"
          value={approver}
          onChange={(e) => setApprover(e.target.value)}
          className="rounded-lg bg-white/[0.04] border border-white/10 px-3 py-1.5 text-sm text-neutral-100"
          placeholder="your name"
        />
        {!canApprove && (
          <span className="text-xs text-amber-300/80">
            Name an approver to enable promotion.
          </span>
        )}
      </div>

      {data && data.versions.length === 0 && (
        <p className="text-neutral-500 text-sm">No versions yet for this prompt.</p>
      )}

      <div className="space-y-2">
        {data?.versions.map((v) => (
          <div
            key={v.id}
            data-testid={`version-row-${v.version}`}
            className={
              "rounded-xl border p-4 space-y-2 " +
              (v.is_active
                ? "border-green-500/40 bg-green-500/[0.06]"
                : "border-white/10 bg-white/[0.03]")
            }
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-neutral-100">{v.version}</span>
              {v.is_active ? (
                <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-green-500/15 text-green-300">
                  Live
                </span>
              ) : (
                <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-white/10 text-neutral-400">
                  Candidate · not live
                </span>
              )}
              {v.parent_version && (
                <span className="ml-auto text-xs text-neutral-500">from {v.parent_version}</span>
              )}
            </div>

            {/* Explainability: rationale + the signal ids that triggered it (inline). */}
            <p className="text-xs text-neutral-300">{v.change_rationale ?? "—"}</p>

            <div className="flex gap-2 pt-1">
              {!v.is_active && (
                <button
                  data-testid={`promote-${v.version}`}
                  disabled={busy || !canApprove}
                  onClick={() => promote(v.version)}
                  className="px-3 py-1.5 rounded-lg bg-green-600/80 hover:bg-green-600 text-white text-xs disabled:opacity-50"
                >
                  Approve & Promote
                </button>
              )}
              {v.is_active && v.parent_version && (
                <button
                  data-testid="rollback"
                  disabled={busy}
                  onClick={rollback}
                  className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs disabled:opacity-50"
                >
                  Roll back to {active?.parent_version}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Trial deltas: A/B candidate vs incumbent. */}
      {data?.experiments.map((exp) => (
        <div key={exp.experiment_id} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
          <div className="text-xs text-neutral-400 mb-1">Trial · {exp.status}</div>
          <div className="flex gap-4">
            {exp.variants.map((vr) => (
              <div key={vr.id} className="text-xs text-neutral-300">
                <span className="font-medium">{vr.version ?? vr.label}</span>{" "}
                <span className="tabular-nums text-neutral-400">
                  {(vr.conversion_rate * 100).toFixed(1)}% ({vr.conversions}/{vr.impressions})
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Audit: who promoted/rolled back what, when. */}
      <div>
        <h3 className="text-xs font-semibold text-neutral-300 mb-2">Audit Trail</h3>
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-white/[0.04] text-neutral-400">
              <tr>
                <th className="text-left px-3 py-2">Action</th>
                <th className="text-left px-3 py-2">Change</th>
                <th className="text-left px-3 py-2">By</th>
                <th className="text-left px-3 py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {data?.audit.map((a, i) => (
                <tr key={i} data-testid="audit-row" className="border-t border-white/5 text-neutral-300">
                  <td className="px-3 py-2">{a.action}</td>
                  <td className="px-3 py-2">
                    {a.old_value ?? "—"} → {a.new_value ?? "—"}
                  </td>
                  <td className="px-3 py-2">{a.actor}</td>
                  <td className="px-3 py-2 text-neutral-500">{a.created_at}</td>
                </tr>
              ))}
              {data && data.audit.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-3 text-neutral-500">
                    No transitions recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
