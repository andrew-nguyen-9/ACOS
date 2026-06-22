/**
 * System theme synchronization with a clip-path reveal (Phase 11.8, DMI-001).
 *
 * When the OS theme flips, animate the swap as a circular `clip-path` reveal
 * growing from the last cursor position (read from the 11.5 transient store, so
 * no re-render). The overlay paints the *incoming* background and wipes over the
 * old UI; the theme class is swapped once the overlay fully covers, so the swap
 * itself is never visible.
 *
 * Theme is represented by `data-theme="light"` on <html>; its absence is the
 * designed true-dark default. To preserve that default we sync on live OS
 * *changes* only, not initial load.
 *
 * Reduced-motion → instant class swap, no overlay (clip-path bypass).
 */
import { useEffect } from "react";
import { getPointer } from "@/stores/useTransientInput";
import { prefersReducedMotion } from "@/motion";

type Theme = "light" | "dark";

// Incoming background per theme — mirrors --bg in tokens.css for both modes. Kept
// literal here because the overlay paints before the class swap, so it can't read
// the post-swap token value.
const BG: Record<Theme, string> = { dark: "#0a0a0a", light: "#f5f5f7" };

function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

function applyTheme(theme: Theme): void {
  if (theme === "light") document.documentElement.dataset.theme = "light";
  else delete document.documentElement.dataset.theme;
}

function reveal(theme: Theme): void {
  if (theme === currentTheme()) return;
  if (prefersReducedMotion()) {
    applyTheme(theme);
    return;
  }

  const { x, y } = getPointer();
  const radius = Math.hypot(
    Math.max(x, window.innerWidth - x),
    Math.max(y, window.innerHeight - y),
  );

  const overlay = document.createElement("div");
  overlay.setAttribute("aria-hidden", "true");
  overlay.style.cssText =
    `position:fixed;inset:0;z-index:2147483647;pointer-events:none;` +
    `background:${BG[theme]};will-change:clip-path;`;
  document.body.appendChild(overlay);

  const anim = overlay.animate(
    [
      { clipPath: `circle(0px at ${x}px ${y}px)` },
      { clipPath: `circle(${radius}px at ${x}px ${y}px)` },
    ],
    { duration: 520, easing: "cubic-bezier(0.32,0.72,0,1)", fill: "forwards" },
  );

  // Swap the class once the overlay fully covers the viewport — invisible because
  // the overlay already shows the incoming background.
  const finish = () => {
    applyTheme(theme);
    overlay.remove();
  };
  anim.finished.then(finish).catch(finish);
}

export function useThemeReveal(): void {
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onMq = (e: MediaQueryListEvent) => reveal(e.matches ? "dark" : "light");
    mq.addEventListener("change", onMq);

    // Tauri native theme events (prod / packaged app only) — guarded dynamic
    // import like the 11.7 clock, so vite dev / jsdom resolve but never fire.
    let unlisten: (() => void) | undefined;
    if (import.meta.env.PROD) {
      void import("@tauri-apps/api/window")
        .then(({ getCurrentWindow }) =>
          getCurrentWindow().onThemeChanged(({ payload }) =>
            reveal(payload === "light" ? "light" : "dark"),
          ),
        )
        .then((fn) => {
          unlisten = fn;
        })
        .catch(() => {});
    }

    return () => {
      mq.removeEventListener("change", onMq);
      unlisten?.();
    };
  }, []);
}
