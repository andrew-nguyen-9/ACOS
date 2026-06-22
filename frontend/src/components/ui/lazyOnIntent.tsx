import { lazy, type ComponentType, type LazyExoticComponent } from "react";

/**
 * Code-split a component, but warm its chunk on user intent (PERF-IL-001).
 *
 * `React.lazy` only fetches the chunk when the component first renders — too
 * late if the user just clicked. Call `prefetch()` on `onPointerEnter` (hover/
 * focus) so the chunk is already in the module cache by the time they click.
 * The dynamic import is deduped: prefetch + the eventual lazy render resolve the
 * same module, and `prefetch` itself fires the importer at most once.
 */
type Importer<P> = () => Promise<{ default: ComponentType<P> }>;

export interface LazyOnIntent<P> {
  Component: LazyExoticComponent<ComponentType<P>>;
  prefetch: () => void;
}

export function lazyOnIntent<P = Record<string, never>>(
  importer: Importer<P>,
): LazyOnIntent<P> {
  let started: Promise<unknown> | null = null;
  const prefetch = () => {
    started ??= importer();
  };
  return { Component: lazy(importer), prefetch };
}
