import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/navigate", () => ({
  hardNavigate: vi.fn(),
}));

import LoginPage from "@/app/(public)/auth/login/page";
import { Providers } from "@/components/providers";

function renderLogin() {
  return render(
    <Providers>
      <LoginPage />
    </Providers>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          csrf_token: "test-csrf",
          user: {
            id: "00000000-0000-0000-0000-000000000001",
            name: "Alice",
            email: "alice@example.com",
            phone: "+254700000000",
            role: "landlord",
            is_verified: true,
            tenant_code: null,
          },
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    );
  });
  afterEach(() => vi.restoreAllMocks());

  it("rejects empty submit with inline errors", async () => {
    renderLogin();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    const alerts = await screen.findAllByRole("alert");
    expect(alerts.length).toBeGreaterThanOrEqual(1);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("rejects malformed identifier inline", async () => {
    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email or phone/i), "not-an-email");
    await user.type(screen.getByLabelText(/password/i), "secret");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/use a valid email or phone/i)).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("submits when input is valid", async () => {
    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email or phone/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "S3cretPass!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (global.fetch as unknown as ReturnType<typeof vi.fn>)
      .mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/auth\/login$/);
    expect(init.method).toBe("POST");
    expect(init.body).toContain("alice@example.com");
  });
});
