/** Auth helpers using the FastAPI JWT-cookie session. */
import { api } from "./api";

export type UserRole = "landlord" | "tenant" | "admin";

export interface UserOut {
  id: string;
  name: string;
  email: string | null;
  phone: string;
  role: UserRole;
  is_verified: boolean;
  tenant_code: string | null;
}

export async function whoami(): Promise<UserOut | null> {
  try {
    return await api<UserOut>("/auth/whoami");
  } catch {
    return null;
  }
}

export async function login(opts: {
  identifier: string;
  password: string;
}): Promise<UserOut> {
  return api<UserOut>("/auth/login", {
    method: "POST",
    body: opts,
  });
}

export async function logout(): Promise<void> {
  await api("/auth/logout", { method: "POST" });
}
