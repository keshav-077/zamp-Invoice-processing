import { describe, expect, it } from "vitest";

import { formatMoney } from "./api";

describe("formatMoney", () => {
  it("preserves missing values instead of manufacturing zero", () => {
    expect(formatMoney(null)).toBe("Not found");
    expect(formatMoney(undefined)).toBe("Not found");
  });

  it("formats a real numeric zero", () => {
    expect(formatMoney(0, "USD")).toBe("$0.00");
  });
});
