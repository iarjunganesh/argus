import { describe, expect, it } from "vitest";

import { recalledEntityName, rememberEntityName } from "./session";

function memoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (name) => items.get(name) ?? null,
    key: (index) => [...items.keys()][index] ?? null,
    removeItem: (name) => void items.delete(name),
    setItem: (name, value) => void items.set(name, value),
  };
}

function brokenStorage(): Storage {
  const fail = () => {
    throw new Error("blocked");
  };
  return { ...memoryStorage(), getItem: fail, setItem: fail };
}

describe("the entity name for an assessment", () => {
  it("is recalled for the same report ID only", () => {
    const storage = memoryStorage();
    rememberEntityName("r1", "Wirecard AG", storage);
    expect(recalledEntityName("r1", storage)).toBe("Wirecard AG");
    expect(recalledEntityName("r2", storage)).toBeUndefined();
  });

  it("is simply missing when storage is unavailable or blocked", () => {
    rememberEntityName("r1", "Wirecard AG", undefined);
    expect(recalledEntityName("r1", undefined)).toBeUndefined();
    expect(() => rememberEntityName("r1", "Wirecard AG", brokenStorage())).not.toThrow();
    expect(recalledEntityName("r1", brokenStorage())).toBeUndefined();
  });
});
