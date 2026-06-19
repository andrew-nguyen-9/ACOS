import { Settings } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";

export default function SettingsPage() {
  return (
    <div className="p-8 flex flex-col gap-6 h-full">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Settings</h1>
        <p className="text-[#a1a1a1] text-sm mt-1">Application configuration</p>
      </div>
      <GlassCard className="p-8 flex items-center justify-center flex-1">
        <div className="text-center">
          <Settings className="size-8 text-neutral-600 mx-auto mb-3" />
          <p className="text-[#a1a1a1] text-sm">Settings coming soon</p>
        </div>
      </GlassCard>
    </div>
  );
}
