import { describe, expect, it } from "vitest";
import { formatDate, formatKES } from "@/lib/format";

describe("formatKES", () => {
  it("formats integers with the KES prefix and grouping", () => {
    const out = formatKES(25000);
    expect(out).toMatch(/^KES/);
    expect(out).toContain("25,000");
  });

  it("accepts numeric strings", () => {
    expect(formatKES("12345")).toContain("12,345");
  });

  it("falls back to KES 0 for invalid input", () => {
    expect(formatKES(null)).toBe("KES 0");
    expect(formatKES(undefined)).toBe("KES 0");
    expect(formatKES("not-a-number")).toBe("KES 0");
  });
});

describe("formatDate", () => {
  it("formats ISO strings as a short date", () => {
    expect(formatDate("2026-05-09")).toMatch(/2026/);
  });
  it("returns empty for invalid", () => {
    expect(formatDate("oops")).toBe("");
  });
});
