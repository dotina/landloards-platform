import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { Providers } from "@/components/providers";

vi.mock("next/navigation", () => ({
  usePathname: () => "/tenant",
  useRouter: () => ({ push: vi.fn() }),
}));

import TenantHome from "@/app/tenant/page";
import TenantPayPage from "@/app/tenant/pay/page";
import TenantPlanPage from "@/app/tenant/plan/page";
import TenantInboxPage from "@/app/tenant/notifications/page";
import TenantProfilePage from "@/app/tenant/profile/page";
import TenantLeasePage from "@/app/tenant/lease/page";
import TenantHistoryPage from "@/app/tenant/history/page";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Tenant pages", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockImplementation(async () => jsonResponse([]));
  });
  afterEach(() => vi.restoreAllMocks());

  it("Home renders Total due card and CTAs", () => {
    render(
      <Providers>
        <TenantHome />
      </Providers>
    );
    expect(screen.getByText(/total due/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pay now/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view history/i })).toBeInTheDocument();
  });

  it("Pay renders the form when an outstanding invoice exists", async () => {
    vi.spyOn(global, "fetch").mockImplementation(async (url) => {
      if (typeof url === "string" && url.endsWith("/tenant/invoices")) {
        return jsonResponse([
          {
            id: "11111111-1111-1111-1111-111111111111",
            status: "open",
            amount: "25000",
            late_fee_accrued: "0",
            period_start: "2026-05-01",
          },
        ]);
      }
      return jsonResponse([]);
    });
    render(
      <Providers>
        <TenantPayPage />
      </Providers>
    );
    expect(await screen.findByLabelText(/m-pesa phone/i)).toBeInTheDocument();
  });

  it("Plan renders no plans + history empty state initially", () => {
    render(
      <Providers>
        <TenantPlanPage />
      </Providers>
    );
    expect(screen.getByText(/active.*past plans/i)).toBeInTheDocument();
  });

  it("Inbox shows empty state with no notifications", () => {
    render(
      <Providers>
        <TenantInboxPage />
      </Providers>
    );
    expect(screen.getByRole("heading", { name: /inbox/i })).toBeInTheDocument();
  });

  it("Profile renders KYC card and form", () => {
    render(
      <Providers>
        <TenantProfilePage />
      </Providers>
    );
    expect(screen.getByRole("heading", { name: /^profile$/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/upload id/i)).toBeInTheDocument();
  });

  it("Lease shows fallback when no active lease", () => {
    render(
      <Providers>
        <TenantLeasePage />
      </Providers>
    );
    expect(screen.getByRole("heading", { name: /^lease$/i })).toBeInTheDocument();
  });

  it("History shows download statement button", () => {
    render(
      <Providers>
        <TenantHistoryPage />
      </Providers>
    );
    expect(
      screen.getByRole("button", { name: /download statement/i })
    ).toBeInTheDocument();
  });
});
