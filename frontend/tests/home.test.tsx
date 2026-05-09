import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import HomePage from "@/app/page";

describe("HomePage", () => {
  it("renders the brand and the primary CTAs", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /rent management/i
    );
    expect(screen.getAllByRole("link", { name: /get started|create landlord/i }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /sign in/i }).length).toBeGreaterThan(0);
  });
});
