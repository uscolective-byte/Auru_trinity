import { describe, expect, it } from "vitest";
import { ApprovalPolicy } from "../src/policy.js";

describe("ApprovalPolicy", () => {
  const policy = new ApprovalPolicy(
    new Set(["external_write", "send_message"]),
  );

  it("allows non-sensitive actions", () =>
    expect(policy.evaluate("read")).toBe("allow"));
  it("gates sensitive actions", () =>
    expect(policy.evaluate("external_write")).toBe("approval_required"));
  it("honours explicit approval", () =>
    expect(
      policy.evaluate("send_message", { approved: true, actor: "user" }),
    ).toBe("allow"));
  it("denies an explicit rejection", () =>
    expect(
      policy.evaluate("external_write", { approved: false, actor: "user" }),
    ).toBe("deny"));
});
