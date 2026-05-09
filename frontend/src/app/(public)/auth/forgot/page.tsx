"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";

const schema = z.object({
  identifier: z.string().min(1, "Email or phone is required"),
});

type FormValues = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const { push } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    try {
      await api("/auth/forgot", { method: "POST", body: values });
      setDone(true);
      push({
        kind: "info",
        message: "If your account exists, we sent reset instructions.",
      });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Something went wrong.";
      push({ kind: "error", message: msg });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Forgot password</CardTitle>
        <CardDescription>
          Enter the email or phone tied to your account.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {done ? (
          <p className="text-sm text-muted-foreground">
            If your account exists, we&rsquo;ve sent reset instructions. You can
            now <Link className="text-primary hover:underline" href="/auth/login">return to sign-in</Link>.
          </p>
        ) : (
          <form
            aria-label="forgot-form"
            onSubmit={handleSubmit(onSubmit)}
            className="space-y-4"
            noValidate
          >
            <div className="space-y-2">
              <Label htmlFor="identifier">Email or phone</Label>
              <Input
                id="identifier"
                {...register("identifier")}
                aria-invalid={!!errors.identifier}
              />
              {errors.identifier && (
                <p role="alert" className="text-sm text-destructive">
                  {errors.identifier.message}
                </p>
              )}
            </div>
            <Button className="w-full" disabled={submitting}>
              {submitting ? "Sending…" : "Send reset link"}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
