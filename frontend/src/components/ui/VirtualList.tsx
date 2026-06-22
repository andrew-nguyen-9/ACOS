import { type ReactNode, type RefObject } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

/**
 * Virtualized list (Phase 11.6, PERF-RP-003).
 *
 * Renders only the rows in view (+ overscan), keeping DOM node count flat no
 * matter how long the list is (ceiling <1500 nodes). Rows are absolutely
 * positioned and moved with `translateY` (OMTA — no layout per scroll frame),
 * and each carries `content-visibility:auto` so the engine can skip painting
 * off-screen rows entirely (modern WebKit; degrades to ignored elsewhere).
 *
 * The scroll element is owned by the parent (`scrollRef`) so the same element
 * can also drive `useScrollKinematics` (collapsing header / progress).
 */
export interface VirtualListProps<T> {
  items: T[];
  /** The scrollable parent this list lives inside. */
  scrollRef: RefObject<HTMLElement>;
  /** Estimated row height incl. gap, px. Rows self-measure for the exact size. */
  estimateSize?: number;
  overscan?: number;
  renderItem: (item: T, index: number) => ReactNode;
  getKey?: (item: T, index: number) => string | number;
}

export function VirtualList<T>({
  items,
  scrollRef,
  estimateSize = 72,
  overscan = 8,
  renderItem,
  getKey,
}: VirtualListProps<T>) {
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => estimateSize,
    overscan,
  });

  return (
    <div style={{ height: virtualizer.getTotalSize(), position: "relative", width: "100%" }}>
      {virtualizer.getVirtualItems().map((vi) => {
        const item = items[vi.index];
        return (
          <div
            key={getKey ? getKey(item, vi.index) : vi.key}
            data-index={vi.index}
            ref={virtualizer.measureElement}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              transform: `translateY(${vi.start}px)`,
              contentVisibility: "auto",
            }}
          >
            {renderItem(item, vi.index)}
          </div>
        );
      })}
    </div>
  );
}
