import { useState } from "react";
import { CheckCircle, Loader2, AlertTriangle, Zap } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { UploadStep } from "@/components/onboarding/UploadStep";
import { ModelPull } from "@/components/onboarding/ModelPull";
import { apiFetch } from "@/services/api";
import { updateSetting, completeOnboarding } from "@/services/settings";

type Step = "welcome" | "ollama" | "profile" | "done";

interface OllamaStatus {
  available: boolean;
  missing_models: string[];
  degraded: boolean;
}

interface Props {
  onComplete: () => void;
}

export default function FirstRunWizard({ onComplete }: Props) {
  const [step, setStep] = useState<Step>("welcome");
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
  const [checking, setChecking] = useState(false);
  const [model, setModel] = useState("qwen3:8b");
  const [github, setGithub] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function checkOllama() {
    setChecking(true);
    setError(null);
    try {
      const data = await apiFetch<OllamaStatus>("/health/ollama");
      setOllamaStatus(data);
    } catch {
      setOllamaStatus({ available: false, missing_models: [], degraded: true });
      setError("Could not reach the backend. Is the backend running?");
    } finally {
      setChecking(false);
    }
  }

  async function finishSetup() {
    setSaving(true);
    setError(null);
    try {
      await updateSetting("default_model", model);
      if (github.trim()) await updateSetting("github_username", github.trim());
      await completeOnboarding();
      setStep("done");
    } catch {
      setError("Failed to save configuration. Check the backend is running.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#09090b] flex items-center justify-center p-8">
      <GlassCard className="w-full max-w-lg p-8 flex flex-col gap-6">
        <div className="flex items-center gap-3">
          <Zap className="size-6 text-indigo-400" />
          <h1 className="text-xl font-semibold text-neutral-50">Welcome to ACOS</h1>
        </div>

        {step === "welcome" && (
          <>
            <p className="text-neutral-300 text-sm leading-relaxed">
              ACOS is your fully offline AI Career Operating System. It runs entirely on your
              machine — no cloud APIs, no data leaving your device.
            </p>
            <p className="text-neutral-400 text-sm">
              This wizard takes ~2 minutes to complete setup.
            </p>
            <button
              onClick={() => {
                setStep("ollama");
                void checkOllama();
              }}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
            >
              Begin Setup
            </button>
          </>
        )}

        {step === "ollama" && (
          <>
            <div>
              <h2 className="text-neutral-100 font-medium mb-1">Ollama Check</h2>
              <p className="text-neutral-400 text-sm">ACOS uses Ollama to run local AI models.</p>
            </div>
            {checking && (
              <div className="flex items-center gap-2 text-neutral-400 text-sm">
                <Loader2 className="size-4 animate-spin" />
                Checking Ollama…
              </div>
            )}
            {ollamaStatus && !checking && (
              <div className="flex flex-col gap-2">
                <div
                  className={`flex items-center gap-2 text-sm ${
                    ollamaStatus.available ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {ollamaStatus.available ? (
                    <CheckCircle className="size-4" />
                  ) : (
                    <AlertTriangle className="size-4" />
                  )}
                  {ollamaStatus.available ? "Ollama is running" : "Ollama not found"}
                </div>
                {ollamaStatus.available && ollamaStatus.missing_models.length > 0 && (
                  <div className="flex flex-col gap-2 text-sm">
                    <span className="text-amber-400">
                      Missing model{ollamaStatus.missing_models.length > 1 ? "s" : ""}:{" "}
                      {ollamaStatus.missing_models.join(", ")}
                    </span>
                    <ModelPull
                      model={ollamaStatus.missing_models[0]}
                      onDone={() => void checkOllama()}
                    />
                    <p className="text-neutral-500 text-xs">
                      Or pull it yourself:{" "}
                      <code className="bg-neutral-800 px-1 rounded">
                        ollama pull {ollamaStatus.missing_models[0]}
                      </code>
                    </p>
                  </div>
                )}
              </div>
            )}
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="flex gap-3">
              <button
                onClick={() => void checkOllama()}
                disabled={checking}
                className="flex-1 py-2 border border-neutral-700 text-neutral-300 rounded-lg text-sm hover:bg-neutral-800 transition disabled:opacity-50"
              >
                Re-check
              </button>
              <button
                onClick={() => setStep("profile")}
                disabled={!ollamaStatus || checking || !ollamaStatus.available}
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
              >
                {ollamaStatus?.available ? "Continue" : "Ollama Required"}
              </button>
            </div>
            {ollamaStatus && !ollamaStatus.available && !checking && (
              <button
                onClick={() => setStep("profile")}
                data-testid="continue-degraded"
                className="text-neutral-400 hover:text-neutral-200 text-xs underline transition"
              >
                Continue without Ollama (degraded — AI features disabled until it's running)
              </button>
            )}
          </>
        )}

        {step === "profile" && (
          <>
            <div>
              <h2 className="text-neutral-100 font-medium mb-1">Model &amp; Profile</h2>
              <p className="text-neutral-400 text-sm">
                Configure your preferred AI model and GitHub identity.
              </p>
            </div>
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-neutral-300 text-sm">Default Model</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-neutral-100 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="qwen3:8b">Qwen3 8B (recommended)</option>
                  <option value="llama3:8b">Llama 3 8B</option>
                  <option value="mistral:7b">Mistral 7B</option>
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-neutral-300 text-sm">
                  GitHub Username{" "}
                  <span className="text-neutral-500">(optional)</span>
                </label>
                <input
                  type="text"
                  value={github}
                  onChange={(e) => setGithub(e.target.value)}
                  placeholder="your-github-username"
                  className="bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-neutral-100 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
            <UploadStep />
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <button
              onClick={() => void finishSetup()}
              disabled={saving}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition disabled:opacity-50"
            >
              {saving ? "Saving…" : "Finish Setup"}
            </button>
          </>
        )}

        {step === "done" && (
          <>
            <div className="flex items-center gap-2 text-green-400">
              <CheckCircle className="size-5" />
              <span className="font-medium">Setup complete!</span>
            </div>
            <p className="text-neutral-300 text-sm">
              ACOS is ready. Start by ingesting your resume and job descriptions.
            </p>
            <button
              onClick={onComplete}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
            >
              Open ACOS
            </button>
          </>
        )}
      </GlassCard>
    </div>
  );
}
