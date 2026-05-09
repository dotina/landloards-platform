import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { Providers } from "@/components/providers";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "11111111-1111-1111-1111-111111111111" }),
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn() }),
}));

import DashboardOverview from "@/app/dashboard/page";
import InvoicesPage from "@/app/dashboard/invoices/page";
import PlansPage from "@/app/dashboard/plans/page";
import NotificationsPage from "@/app/dashboard/notifications/page";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Dashboard pages", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (typeof url !== "string") return jsonResponse([]);
      if (url.endsWith("/properties")) return jsonResponse([]);
      if (url.includes("/invoices")) return jsonResponse([]);
      if (url.includes("/admin/payments") && !url.includes("c2b"))
        return jsonResponse([]);
      if (url.includes("/admin/payments/c2b/unmatched")) return jsonResponse([]);
      if (url.includes("/admin/plans")) return jsonResponse([]);
      if (url.includes("/admin/notifications")) return jsonResponse([]);
      return jsonResponse([]);
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("renders Overview page header and KPI labels", () => {
    render(
      <Providers>
        <DashboardOverview />
      </Providers>
    );
    expect(screen.getByRole("heading", { name: /overview/i })).toBeInTheDocument();
    expect(screen.getAllByText(/properties/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/outstanding/i).length).toBeGreaterThan(0);
  });

  it("renders Invoices page with status tabs", () => {
    render(
      <Providers>
        <InvoicesPage />
      </Providers>
    );
    expect(screen.getByRole("heading", { name: /invoices/i })).toBeInTheDocument();
    expect(screen.getAllByRole("tab").length).toBeGreaterThanOrEqual(5);
  });

  it("renders Plans page with three tabs", () => {
    render(
      <Providers>
        <PlansPage />
      </Providers>
    );
    expect(screen.getByRole("heading", { name: /payment plans/i })).toBeInTheDocument();
    expect(screen.getAllByRole("tab")).toHaveLength(3);
  });

  it("renders Notifications page header", () => {
    render(
      <Providers>
        <NotificationsPage />
      </Providers>
    );
    expect(
      screen.getByRole("heading", { name: /notifications/i })
    ).toBeInTheDocument();
  });
});
