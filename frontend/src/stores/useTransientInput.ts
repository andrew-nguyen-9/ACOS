import { useRef, type MutableRefObject } from "react";
import { createStore } from "zustand/vanilla";

/**
 * Transient high-frequency input store (Phase 11.5, PERF-RP-001).
 *
 * Pointer/scroll/drag fire dozens of times per frame. Routing those through
 * React `useState` would re-render on every move and tank FPS. This is a
 * *vanilla* Zustand store (no React binding): writes notify imperative
 * `subscribe` listeners and update a live object, but no component re-renders.
 * Animation code reads `usePointerRef().current` inside a rAF loop, or
 * subscribes imperatively to drive a framer-motion `MotionValue`.
 */
export interface Pointer {
  x: number;
  y: number;
}

interface TransientInputState {
  pointer: Pointer;
}

// One stable object, mutated in place. rAF loops hold a ref to it and always
// read the latest position with zero allocation and zero re-renders. The
// zustand store mirrors it (new object per write) only to drive `subscribe`.
const live: Pointer = { x: 0, y: 0 };

const store = createStore<TransientInputState>(() => ({ pointer: { ...live } }));

/** Record the latest pointer position. Does NOT trigger any React render. */
export function setPointer(x: number, y: number): void {
  live.x = x;
  live.y = y;
  store.setState({ pointer: { x, y } });
}

/**
 * Current pointer position. Returns the live, mutable object — read it, don't
 * keep or mutate it (it changes under you each frame, by design).
 */
export function getPointer(): Readonly<Pointer> {
  return live;
}

/** Imperatively observe pointer changes; returns an unsubscribe fn. */
export function subscribePointer(listener: (pointer: Pointer) => void): () => void {
  return store.subscribe((state) => listener(state.pointer));
}

/**
 * Stable ref whose `.current` always reflects the live pointer, without
 * subscribing the component to renders.
 */
export function usePointerRef(): MutableRefObject<Pointer> {
  const ref = useRef<Pointer>(live);
  ref.current = live;
  return ref;
}
