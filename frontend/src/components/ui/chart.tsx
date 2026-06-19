import { type ReactNode } from "react";
import { ResponsiveContainer, Tooltip } from "recharts";

interface ChartContainerProps {
  children: ReactNode;
  className?: string;
  config?: Record<string, { label?: string; color?: string }>;
}

export function ChartContainer({ children, className }: ChartContainerProps) {
  return (
    <ResponsiveContainer width="100%" height="100%" className={className}>
      {children as React.ReactElement}
    </ResponsiveContainer>
  );
}

export function ChartTooltip() {
  return (
    <Tooltip
      contentStyle={{
        background: "rgba(17,20,26,0.95)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: "12px",
        color: "#f5f5f5",
        fontSize: "12px",
      }}
    />
  );
}
