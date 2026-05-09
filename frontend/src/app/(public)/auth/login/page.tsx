"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { login } from "@/lib/auth";
import { ApiError } from "@/lib/api";

const schema = z.object({
  identifier: z
    .string()
    .min(1, "Email or phone is required")
    .refine(
      (v) => v.includes("@") || /^\+?\d{6,}$/.test(v),
      "Use a valid email or phone (e.g. +2547...)."
    ),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
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
    try {
      const user = await login(values);
      push({ kind: "success", message: `Welcome back, ${user.name}` });
      router.push(user.role === "tenant" ? "/tenant" : "/dashboard");
    } catch (e) {
      const msg =
        e instanceof ApiError ? e.message : "Could not sign in. Try again.";
      push({ kind: "error", message: msg });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>
          Use your email or phone number and password.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          aria-label="login-form"
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4"
          noValidate
        >
          <div className="space-y-2">
            <Label htmlFor="identifier">Email or phone</Label>
            <Input
              id="identifier"
              autoComplete="username"
              {...register("identifier")}
              aria-invalid={!!errors.identifier}
            />
            {errors.identifier && (
              <p role="alert" className="text-sm text-destructive">
                {errors.identifier.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register("password")}
              aria-invalid={!!errors.password}
            />
            {errors.password && (
              <p role="alert" className="text-sm text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </Button>

          <div className="flex items-center justify-between text-sm">
            <Link className="text-primary hover:underline" href="/auth/forgot">
              Forgot password
            </Link>
            <Link
              className="text-primary hover:underline"
              href="/auth/landlord/register"
            >
              Create landlord account
            </Link>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
