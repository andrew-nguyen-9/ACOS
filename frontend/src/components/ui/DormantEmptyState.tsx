import { Sparkles } from "lucide-react";
import { EmptyState } from "./EmptyState";

/**
 * The flywheel's "not enough data yet" state (Phase 13.0).
 *
 * Used wherever a surface is empty because it is dormant by design, not broken:
 * a fresh tenant with too few signals, or a cross-tenant aggregate suppressed by
 * k-anonymity (ADR-009). Framed as a calm pending state — never an error — so the
 * privacy floor reads as expected behavior. Thin wrapper over EmptyState for one
 * consistent treatment across 13.1–13.5.
 */
export function DormantEmptyState({
  title = "Not enough data yet",
  description = "Insights appear here as you log more applications and outcomes.",
}: {
  title?: string;
  description?: string;
}) {
  return <EmptyState title={title} description={description} icon={Sparkles} />;
}
