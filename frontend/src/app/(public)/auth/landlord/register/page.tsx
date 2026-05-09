"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { authDebug, hasVisibleCsrfCookie } from "@/lib/auth-debug";
import { api, ApiError } from "@/lib/api";
import type { UserOut } from "@/lib/auth";

const schema = z.object({
  name: z.string().min(2, "Tell us your name"),
  email: z.string().email("Use a valid email"),
  phone: z
    .string()
    .regex(/^\+?\d{9,15}$/, "Use a valid phone (e.g. +2547...)."),
  password: z
    .string()
    .min(8, "At least 8 characters")
    .regex(/[A-Z]/, "Include an upper-case letter")
    .regex(/[a-z]/, "Include a lower-case letter")
    .regex(/\d/, "Include a digit"),
});

type FormValues = z.infer<typeof schema>;

export default function LandlordRegisterPage() {
  const { push } = useToast();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    authDebug("register_submit_start");
    try {
      const user = await api<UserOut>("/auth/landlord/register", {
        method: "POST",
        body: values,
      });
      authDebug("register_api_ok", {
        id: user.id,
        role: user.role,
        ll_csrf_visible: hasVisibleCsrfCookie(),
      });
      push({ kind: "success", message: `Welcome, ${user.name}` });
      authDebug("register_router_push", { href: "/dashboard" });
      router.push("/dashboard");
    } catch (e) {
      authDebug("register_submit_error", {
        kind: e instanceof ApiError ? "ApiError" : "unknown",
        status: e instanceof ApiError ? e.status : undefined,
        message: e instanceof Error ? e.message : String(e),
      });
      const msg =
        e instanceof ApiError ? e.message : "Registration failed. Try again.";
      push({ kind: "error", message: msg });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Create landlord account</CardTitle>
        <CardDescription>
          Set up your Landloads workspace in under a minute.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          aria-label="landlord-register-form"
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4"
          noValidate
        >
          {(["name", "email", "phone", "password"] as const).map((field) => (
            <div key={field} className="space-y-2">
              <Label htmlFor={field}>
                {field === "name"
                  ? "Full name"
                  : field === "email"
                  ? "Email"
                  : field === "phone"
                  ? "Phone (E.164)"
                  : "Password"}
              </Label>
              <Input
                id={field}
                type={field === "password" ? "password" : "text"}
                autoComplete={
                  field === "password" ? "new-password" : field
                }
                {...register(field)}
                aria-invalid={!!errors[field]}
              />
              {errors[field] && (
                <p role="alert" className="text-sm text-destructive">
                  {errors[field]?.message}
                </p>
              )}
            </div>
          ))}

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            By creating an account you agree to our{" "}
            <a
              href="/privacy"
              className="text-primary hover:underline"
            >
              privacy notice
            </a>
            .
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
