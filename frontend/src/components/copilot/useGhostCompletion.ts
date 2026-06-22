/**
 * Ghost-completion state machine + hook (Phase 11.8, COP-003).
 *
 * The copilot suggests how to finish the current input; the suggestion renders
 * as faint inline ghost text in an overlay layer (never the input value — that
 * would fight IME / controlled input). `Tab` accepts, `Esc` dismisses.
 *
 * The reducer below is the pure, unit-tested core. `dismissed` suppresses any
 * suggestion that streams in afterward (no flicker) until the user types again.
 */
import { useCallback, useEffect, useReducer, useRef } from "react";
import { copilotService } from "@/services/copilot";

export type GhostStatus = "idle" | "showing" | "dismissed";

export interface GhostState {
  suggestion: string;
  status: GhostStatus;
}

export const initialGhost: GhostState = { suggestion: "", status: "idle" };

export type GhostAction =
  | { type: "suggest"; suggestion: string }
  | { type: "accept" }
  | { type: "dismiss" }
  | { type: "input" };

export function ghostReducer(state: GhostState, action: GhostAction): GhostState {
  switch (action.type) {
    case "suggest":
      // A late suggestion after the user dismissed is ignored until they type.
      if (state.status === "dismissed") return state;
      return action.suggestion
        ? { suggestion: action.suggestion, status: "showing" }
        : { suggestion: "", status: "idle" };
    case "accept":
      return initialGhost;
    case "dismiss":
      return { suggestion: "", status: "dismissed" };
    case "input":
      return initialGhost;
  }
}

const DEBOUNCE_MS = 350;
const MIN_CHARS = 8;

/**
 * Drive ghost completions for a single-line input.
 *
 * `value` is the controlled input text. After a debounce the hook asks copilot
 * for a continuation and shows it as ghost text. Returns the ghost string, an
 * `onKeyDown` that consumes Tab/Esc, and an `onValueChange` the input calls so
 * the machine resets the dismissed lock when the user edits.
 */
export function useGhostCompletion(
  value: string,
  onAccept: (full: string) => void,
  enabled = true,
) {
  const [state, dispatch] = useReducer(ghostReducer, initialGhost);
  const valueRef = useRef(value);
  valueRef.current = value;

  // Debounced fetch. Cancels in-flight work on every keystroke; a stale response
  // is dropped if the input moved on (`reqValue !== valueRef.current`).
  useEffect(() => {
    if (!enabled || value.trim().length < MIN_CHARS) {
      dispatch({ type: "suggest", suggestion: "" });
      return;
    }
    let cancelled = false;
    const reqValue = value;
    const id = setTimeout(async () => {
      try {
        const text = await copilotService.complete(reqValue);
        if (!cancelled && reqValue === valueRef.current) {
          dispatch({ type: "suggest", suggestion: text });
        }
      } catch {
        /* offline / no suggestion — leave ghost untouched */
      }
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [value, enabled]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent): boolean => {
      if (state.status !== "showing") return false;
      if (e.key === "Tab") {
        e.preventDefault();
        onAccept(valueRef.current + state.suggestion);
        dispatch({ type: "accept" });
        return true;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        dispatch({ type: "dismiss" });
        return true;
      }
      return false;
    },
    [state, onAccept],
  );

  const onValueChange = useCallback(() => dispatch({ type: "input" }), []);

  return {
    ghost: state.status === "showing" ? state.suggestion : "",
    onKeyDown,
    onValueChange,
  };
}
