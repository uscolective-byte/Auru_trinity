import { describe, expect, it } from "vitest";
import { MemoryStore } from "../src/memory.js";

describe("MemoryStore", () => {
  it("stores values and evicts the oldest item at its bound", () => {
    const memory = new MemoryStore(2);
    memory.set("a", "one");
    memory.set("b", "two");
    memory.set("c", "three");
    expect(memory.get("a")).toBeUndefined();
    expect(memory.entries()).toEqual([
      { key: "b", value: "two" },
      { key: "c", value: "three" },
    ]);
  });

  it("validates construction and keys", () => {
    expect(() => new MemoryStore(0)).toThrow();
    expect(() => new MemoryStore(1).set(" ", "value")).toThrow();
  });
});
