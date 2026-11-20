export interface AppConfig {
  environment: "development" | "test" | "production";
  memoryLimit: number;
  approvalRequiredFor: readonly ("external_write" | "send_message")[];
}

export function validateConfig(value: unknown): AppConfig {
  if (!value || typeof value !== "object")
    throw new Error("Configuration must be an object");
  const config = value as Record<string, unknown>;
  const environments = ["development", "test", "production"];
  if (!environments.includes(String(config.environment)))
    throw new Error("Invalid environment");
  if (!Number.isInteger(config.memoryLimit) || Number(config.memoryLimit) < 1)
    throw new Error("memoryLimit must be a positive integer");
  const allowed = ["external_write", "send_message"];
  if (
    !Array.isArray(config.approvalRequiredFor) ||
    config.approvalRequiredFor.some((item) => !allowed.includes(String(item)))
  )
    throw new Error("Invalid approval rule");
  return config as unknown as AppConfig;
}
