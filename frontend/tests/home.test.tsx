import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import HomePage from "@/app/page";

describe("HomePage", () => {
  it("renders the brand and the API base hint", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: /landloads/i })).toBeInTheDocument();
    expect(screen.getByTestId("health-link")).toHaveTextContent("/api");
  });
});
