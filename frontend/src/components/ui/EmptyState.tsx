import { type LucideIcon } from "lucide-react";

export function EmptyState({
  title,
  description,
  icon: Icon,
}: {
  title: string;
  description: string;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 py-16 text-center">
      {Icon && (
        <div className="size-12 rounded-2xl bg-neutral-200/[0.08] flex items-center justify-center">
          <Icon className="size-6 text-[#a1a1a1]" />
        </div>
      )}
      <div>
        <p className="font-semibold text-neutral-200 text-base">{title}</p>
        <p className="text-[#a1a1a1] text-sm mt-1 max-w-xs">{description}</p>
      </div>
    </div>
  );
}
