import { cn } from "@/lib/utils";
import { type ReactNode } from "react";
import { useSpecular } from "@/webgl/useSpecular";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  /** Opt in to the cursor-mapped specular highlight (HAM-002). */
  specular?: boolean;
}

export function GlassCard({ children, className, onClick, specular }: GlassCardProps) {
  // Hook is always called (rules of hooks); the ref only attaches when opted in,
  // so non-specular cards never subscribe to the pointer store.
  const specularRef = useSpecular<HTMLDivElement>();
  return (
    <div
      ref={specular ? specularRef : undefined}
      className={cn(
        "rounded-2xl bg-white/[0.05] border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_18px_50px_rgba(0,0,0,0.28)]",
        specular && "specular-surface",
        className,
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
