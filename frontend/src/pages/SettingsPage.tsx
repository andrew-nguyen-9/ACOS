import { useEffect, useState } from "react";
import { Settings, Save, Sparkles } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { getSettings, updateSetting } from "@/services/settings";
import {
  getEffectPreference,
  setEffectPreference,
  supportsWebGL,
  type EffectTier,
} from "@/lib/capability";

const EFFECT_TIERS: { value: EffectTier; label: string; hint: string }[] = [
  { value: "full", label: "Full", hint: "Animated WebGL material + cursor highlights" },
  { value: "reduced", label: "Reduced", hint: "Lighter material, no cursor effects" },
  { value: "off", label: "Off", hint: "Static background — lowest power" },
];

function VisualEffectsControl() {
  const [pref, setPref] = useState<EffectTier>(getEffectPreference);
  const webgl = supportsWebGL();

  function choose(value: EffectTier) {
    setPref(value);
    setEffectPreference(value);
    // Tell the live material to re-resolve its tier without a reload.
    window.dispatchEvent(new Event("acos:effects-changed"));
  }

  return (
    <GlassCard className="p-6 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Sparkles className="size-4 text-neutral-500" />
        <span className="text-neutral-400 text-xs font-medium uppercase tracking-wider">
          Visual Effects
        </span>
      </div>
      <div className="flex gap-2">
        {EFFECT_TIERS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => choose(value)}
            className={
              "flex-1 rounded-lg px-3 py-2 text-sm font-medium transition " +
              (pref === value
                ? "bg-indigo-600 text-white"
                : "bg-neutral-900 text-neutral-300 hover:bg-neutral-800")
            }
          >
            {label}
          </button>
        ))}
      </div>
      <p className="text-neutral-500 text-xs">
        {EFFECT_TIERS.find((t) => t.value === pref)?.hint}
      </p>
      {!webgl && (
        <p className="text-weak text-xs">
          WebGL is unavailable on this display — effects run as Off regardless of choice.
        </p>
      )}
    </GlassCard>
  );
}

const EDITABLE_LABELS: Record<string, string> = {
  default_model: "Default LLM Model",
  embedding_model: "Embedding Model",
  github_username: "GitHub Username",
  learning_trigger_count: "Learning Trigger (# applications)",
  ats_keyword_weight: "ATS Keyword Weight",
  ats_skill_weight: "ATS Skill Weight",
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [dirty, setDirty] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then((s) => setSettings(s))
      .catch(() => setError("Failed to load settings"));
  }, []);

  function handleChange(key: string, value: string) {
    setDirty((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      for (const [key, value] of Object.entries(dirty)) {
        await updateSetting(key, value);
      }
      setSettings((prev) => ({ ...prev, ...dirty }));
      setDirty({});
      setSaved(true);
    } catch {
      setError("Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  const displaySettings = { ...settings, ...dirty };
  const hasDirty = Object.keys(dirty).length > 0;

  return (
    <div className="p-8 flex flex-col gap-6 h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Settings</h1>
          <p className="text-[#a1a1a1] text-sm mt-1">Model configuration and preferences</p>
        </div>
        {hasDirty && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition disabled:opacity-50"
          >
            <Save className="size-4" />
            {saving ? "Saving…" : "Save Changes"}
          </button>
        )}
      </div>

      {error && (
        <div className="text-red-400 text-sm px-4 py-2 bg-red-900/20 rounded-lg">{error}</div>
      )}
      {saved && !hasDirty && (
        <div className="text-green-400 text-sm px-4 py-2 bg-green-900/20 rounded-lg">Settings saved.</div>
      )}

      <VisualEffectsControl />

      <GlassCard className="p-6 flex flex-col gap-5">
        {Object.entries(EDITABLE_LABELS).map(([key, label]) => (
          <div key={key} className="flex flex-col gap-1.5">
            <label className="text-neutral-300 text-sm font-medium">{label}</label>
            <input
              type="text"
              value={displaySettings[key] ?? ""}
              onChange={(e) => handleChange(key, e.target.value)}
              className="bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-neutral-100 text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>
        ))}
      </GlassCard>

      <GlassCard className="p-6">
        <div className="flex items-center gap-2 mb-3">
          <Settings className="size-4 text-neutral-500" />
          <span className="text-neutral-400 text-xs font-medium uppercase tracking-wider">System</span>
        </div>
        <div className="grid grid-cols-2 gap-x-8 gap-y-2">
          {Object.entries(settings)
            .filter(([k]) => !EDITABLE_LABELS[k])
            .map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs">
                <span className="text-neutral-500">{k}</span>
                <span className="text-neutral-300">{v}</span>
              </div>
            ))}
        </div>
      </GlassCard>
    </div>
  );
}
