import { useState } from "react";
import { Download, CheckCircle, AlertTriangle, Loader2 } from "lucide-react";
import { pullModel, type PullProgress } from "@/services/ollama";

/**
 * 13.7 consent-gated model pull. Renders a Download button (no auto-pull); on
 * click, streams progress from the backend. On completion, calls onDone so the
 * wizard can re-check Ollama.
 */
export function ModelPull({ model, onDone }: { model: string; onDone: () => void }) {
  const [state, setState] = useState<"idle" | "pulling" | "done" | "error">("idle");
  const [pct, setPct] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setState("pulling");
    setError(null);
    setPct(null);
    try {
      await pullModel(model, (p: PullProgress) => {
        if (p.total && p.completed != null) {
          setPct(Math.round((p.completed / p.total) * 100));
        }
      });
      setState("done");
      onDone();
    } catch (e) {
      setState("error");
      setError(e instanceof Error ? e.message : "Pull failed");
    }
  }

  if (state === "done") {
    return (
      <div className="flex items-center gap-2 text-green-400 text-sm" data-testid="pull-done">
        <CheckCircle className="size-4" /> {model} downloaded
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {state !== "pulling" ? (
        <button
          onClick={() => void start()}
          data-testid="pull-button"
          className="inline-flex items-center justify-center gap-2 py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
        >
          <Download className="size-4" />
          {state === "error" ? `Retry download ${model}` : `Download ${model}`}
        </button>
      ) : (
        <div className="flex flex-col gap-1" data-testid="pull-progress">
          <div className="flex items-center gap-2 text-neutral-300 text-sm">
            <Loader2 className="size-4 animate-spin" />
            Downloading {model}… {pct != null ? `${pct}%` : ""}
          </div>
          <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 transition-all"
              style={{ width: `${pct ?? 5}%` }}
            />
          </div>
        </div>
      )}
      {error && (
        <p className="flex items-center gap-1.5 text-red-400 text-xs">
          <AlertTriangle className="size-3.5" /> {error}
        </p>
      )}
    </div>
  );
}
