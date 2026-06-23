import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Signed, 2-decimal ROI string (shared by the flywheel ROI sections). */
export function fmtRoi(roi: number): string {
  return `${roi >= 0 ? "+" : ""}${roi.toFixed(2)}`;
}
