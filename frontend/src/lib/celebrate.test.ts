import { describe, it, expect, vi } from "vitest";
import { emitCelebrate, onCelebrate } from "./celebrate";

describe("celebrate bus", () => {
  it("delivers emitted words to every subscriber", () => {
    const a = vi.fn();
    const b = vi.fn();
    onCelebrate(a);
    onCelebrate(b);
    emitCelebrate(["Python", "ETL"]);
    expect(a).toHaveBeenCalledWith(["Python", "ETL"]);
    expect(b).toHaveBeenCalledWith(["Python", "ETL"]);
  });

  it("stops delivering after unsubscribe", () => {
    const cb = vi.fn();
    const off = onCelebrate(cb);
    off();
    emitCelebrate(["x"]);
    expect(cb).not.toHaveBeenCalled();
  });
});
