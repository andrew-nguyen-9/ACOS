import { useState } from "react";
import { Upload, FileText, CheckCircle, Loader2, AlertTriangle, Sparkles } from "lucide-react";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ingestDocument, pollIngest, getOnboardingSummary } from "@/services/ingestion";
import type { OnboardingSummary } from "@/types/onboarding";

const ACCEPT = ".txt,.md,.markdown,.pdf,.docx";

interface FileState {
  name: string;
  status: "uploading" | "processing" | "done" | "failed";
  error?: string;
}

/**
 * 13.5 onboarding upload sub-step. Posts files to the existing validated /ingest
 * endpoint, polls each to a terminal state, then surfaces the built profile
 * (skills + Career-Voice) read from /onboarding/summary.
 *
 * Entirely optional: not uploading is a valid path — the wizard's Finish Setup
 * stays reachable regardless of what happens here.
 */
export function UploadStep() {
  const [files, setFiles] = useState<FileState[]>([]);
  const [summary, setSummary] = useState<OnboardingSummary | null>(null);
  const [busy, setBusy] = useState(false);

  function patch(name: string, next: Partial<FileState>) {
    setFiles((prev) => prev.map((f) => (f.name === name ? { ...f, ...next } : f)));
  }

  async function onSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(e.target.files ?? []);
    if (picked.length === 0) return;
    e.target.value = ""; // allow re-selecting the same file
    setBusy(true);
    setFiles((prev) => [
      ...prev,
      ...picked.map((f) => ({ name: f.name, status: "uploading" as const })),
    ]);

    await Promise.all(
      picked.map(async (file) => {
        try {
          const { job_id } = await ingestDocument(file);
          patch(file.name, { status: "processing" });
          const job = await pollIngest(job_id, (j) =>
            patch(file.name, { status: j.status === "queued" ? "processing" : j.status }),
          );
          patch(file.name, {
            status: job.status === "done" ? "done" : "failed",
            error: job.error,
          });
        } catch (err) {
          patch(file.name, {
            status: "failed",
            error: err instanceof Error ? err.message : "Upload failed",
          });
        }
      }),
    );

    try {
      setSummary(await getOnboardingSummary());
    } catch {
      // Non-blocking: the wizard is still completable without the summary.
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h3 className="text-neutral-100 text-sm font-medium">Build your profile (optional)</h3>
        <p className="text-neutral-400 text-xs mt-0.5">
          Upload résumés, cover letters, or job history. ACOS extracts your skills and writing
          voice — locally. You can skip this and add documents later.
        </p>
      </div>

      <label className="flex items-center justify-center gap-2 border border-dashed border-neutral-700 rounded-lg py-4 text-sm text-neutral-300 cursor-pointer hover:border-indigo-500 hover:text-neutral-100 transition">
        <Upload className="size-4" />
        Choose documents
        <input
          type="file"
          multiple
          accept={ACCEPT}
          onChange={onSelect}
          disabled={busy}
          className="hidden"
          data-testid="onboarding-file-input"
        />
      </label>

      {files.length > 0 && (
        <ul className="flex flex-col gap-1.5" data-testid="file-list">
          {files.map((f) => (
            <li key={f.name} className="flex items-center gap-2 text-xs text-neutral-300">
              {f.status === "done" ? (
                <CheckCircle className="size-3.5 text-green-400" />
              ) : f.status === "failed" ? (
                <AlertTriangle className="size-3.5 text-red-400" />
              ) : (
                <Loader2 className="size-3.5 animate-spin text-neutral-400" />
              )}
              <FileText className="size-3.5 text-neutral-500" />
              <span className="truncate">{f.name}</span>
              {f.status === "failed" && f.error && (
                <span className="text-red-400 truncate">— {f.error}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {summary && <SummaryView summary={summary} />}
    </div>
  );
}

function SummaryView({ summary }: { summary: OnboardingSummary }) {
  const voice = summary.career_voice;
  return (
    <div className="flex flex-col gap-3 border-t border-neutral-800 pt-3" data-testid="summary">
      <div>
        <h4 className="text-neutral-200 text-xs font-medium mb-1.5">
          Skills extracted{summary.documents.count > 0 && ` · from ${summary.documents.count} document(s)`}
        </h4>
        {summary.skills.length === 0 ? (
          <EmptyState
            title="No skills yet"
            description="Upload a résumé to extract skills, or skip — you can add documents anytime."
            icon={FileText}
          />
        ) : (
          <div className="flex flex-wrap gap-1.5" data-testid="skill-chips">
            {summary.skills.map((s) => (
              <span
                key={s.label}
                className="inline-flex items-center gap-1.5 bg-neutral-900 border border-neutral-700 rounded-full px-2.5 py-0.5 text-xs text-neutral-200"
              >
                {s.label}
                <ConfidenceBadge level={s.confidence} />
              </span>
            ))}
          </div>
        )}
      </div>

      <div>
        <h4 className="flex items-center gap-1.5 text-neutral-200 text-xs font-medium mb-1.5">
          <Sparkles className="size-3.5 text-indigo-400" />
          Career-Voice
          {voice.synthetic && (
            <span
              data-testid="synthetic-label"
              className="inline-flex items-center rounded-full border border-[#FF9F0A]/20 bg-[#FF9F0A]/10 px-2 py-0.5 text-[10px] font-medium text-[#FF9F0A]"
            >
              Synthetic — starter template, not from your writing
            </span>
          )}
        </h4>
        <p className="text-neutral-400 text-xs">
          Tone: {voice.tone_descriptors.join(", ") || "—"}
        </p>
        {voice.sample_sentences[0] && (
          <p className="text-neutral-500 text-xs italic mt-1">“{voice.sample_sentences[0]}”</p>
        )}
      </div>
    </div>
  );
}
