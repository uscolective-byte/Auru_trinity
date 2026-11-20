import { describe, expect, it } from "vitest";
import { validateConfig } from "../src/config.js";

describe("configuration validation", () => {
  it("accepts a complete configuration", () => {
    expect(
      validateConfig({
        environment: "test",
        memoryLimit: 10,
        approvalRequiredFor: ["external_write"],
      }),
    ).toMatchObject({ environment: "test", memoryLimit: 10 });
  });

  it.each([
    null,
    { environment: "staging", memoryLimit: 1, approvalRequiredFor: [] },
    { environment: "test", memoryLimit: 0, approvalRequiredFor: [] },
    { environment: "test", memoryLimit: 1, approvalRequiredFor: ["read"] },
  ])("rejects invalid configuration %#", (config) =>
    expect(() => validateConfig(config)).toThrow(),
  );
});
