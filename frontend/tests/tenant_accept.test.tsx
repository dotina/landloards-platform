import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ token: "abc.token.def" }),
}));

import AcceptInvitePage from "@/app/(public)/auth/tenant/accept/[token]/page";
import { Providers } from "@/components/providers";

const userId = "00000000-0000-0000-0000-000000000001";

function makeFetch() {
  return vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (method === "GET" && url.endsWith(`/auth/tenant/accept/abc.token.def`)) {
      return new Response(
        JSON.stringify({ user_id: userId, phone_masked: "+254••••1234" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
}

describe("AcceptInvitePage", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockImplementation(makeFetch());
  });
  afterEach(() => vi.restoreAllMocks());

  it("resolves the invite token then renders the OTP step", async () => {
    render(
      <Providers>
        <AcceptInvitePage />
      </Providers>
    );

    expect(
      await screen.findByLabelText(/6-digit code/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^verify/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /send code/i })
    ).toBeInTheDocument();
  });

  it("requests an OTP via POST when the user clicks Send code", async () => {
    render(
      <Providers>
        <AcceptInvitePage />
      </Providers>
    );
    await screen.findByLabelText(/6-digit code/i);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /send code/i }));

    await waitFor(() => {
      const calls = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
        .calls as Array<[string, RequestInit | undefined]>;
      expect(
        calls.some(
          ([u, init]) =>
            u.endsWith("/auth/tenant/otp/request") && init?.method === "POST"
        )
      ).toBe(true);
    });
  });

  it("rejects an OTP code that is not 6 digits", async () => {
    render(
      <Providers>
        <AcceptInvitePage />
      </Providers>
    );
    await screen.findByLabelText(/6-digit code/i);

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/6-digit code/i), "123");
    await user.click(screen.getByRole("button", { name: /^verify/i }));

    expect(
      await screen.findByText(/enter the 6-digit code/i)
    ).toBeInTheDocument();
  });
});
