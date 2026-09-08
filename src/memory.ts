export interface MemoryEntry {
  key: string;
  value: string;
}

/** Bounded, process-local memory. Untrusted content never becomes instructions. */
export class MemoryStore {
  readonly #entries = new Map<string, string>();
  constructor(private readonly limit: number) {
    if (!Number.isInteger(limit) || limit < 1)
      throw new Error("Memory limit must be positive");
  }

  set(key: string, value: string): void {
    if (!key.trim()) throw new Error("Memory key is required");
    this.#entries.delete(key);
    this.#entries.set(key, value);
    while (this.#entries.size > this.limit)
      this.#entries.delete(this.#entries.keys().next().value!);
  }

  get(key: string): string | undefined {
    return this.#entries.get(key);
  }

  entries(): MemoryEntry[] {
    return [...this.#entries].map(([key, value]) => ({ key, value }));
  }
}
