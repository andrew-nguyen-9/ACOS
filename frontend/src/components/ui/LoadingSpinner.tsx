import { cn } from "@/lib/utils";

const SIZE_MAP = { sm: "size-4", md: "size-6", lg: "size-8" };

export function LoadingSpinner({
  size = "md",
  label,
  className,
}: {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      <div
        className={cn(
          "animate-spin rounded-full border-2 border-white/20 border-t-[#4c8dff]",
          SIZE_MAP[size]
        )}
      />
      {label && <p className="text-[#a1a1a1] text-sm">{label}</p>}
    </div>
  );
}
