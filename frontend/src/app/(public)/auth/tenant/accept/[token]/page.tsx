"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
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
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";

type Step = "loading" | "otp" | "password" | "done";

interface InviteResolved {
  user_id: string;
  phone_masked: string;
}

const otpSchema = z.object({
  code: z.string().regex(/^\d{6}$/, "Enter the 6-digit code we sent"),
});
const passwordSchema = z
  .object({
    password: z
      .string()
      .min(8, "At least 8 characters")
      .regex(/[A-Z]/, "Include an upper-case letter")
      .regex(/[a-z]/, "Include a lower-case letter")
      .regex(/\d/, "Include a digit"),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });

export default function AcceptInvitePage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const { push } = useToast();
  const [step, setStep] = useState<Step>("loading");
  const [invite, setInvite] = useState<InviteResolved | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api<InviteResolved>(
          `/auth/tenant/accept/${encodeURIComponent(params.token)}`
        );
        if (!cancelled) {
          setInvite(res);
          setStep("otp");
        }
      } catch (e) {
        const msg =
          e instanceof ApiError ? e.message : "Invite link is invalid.";
        push({ kind: "error", message: msg });
        if (!cancelled) router.replace("/auth/login");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.token, router, push]);

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Accept your tenant invite</CardTitle>
        <CardDescription>
          We&rsquo;ll text a verification code to{" "}
          <span className="font-medium text-foreground">
            {invite?.phone_masked ?? "your phone"}
          </span>
          .
        </CardDescription>
      </CardHeader>
      <CardContent>
        {step === "loading" && (
          <div className="space-y-3">
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
          </div>
        )}
        {step === "otp" && invite && (
          <OtpStep
            userId={invite.user_id}
            onSuccess={() => setStep("password")}
          />
        )}
        {step === "password" && invite && (
          <PasswordStep
            userId={invite.user_id}
            onSuccess={() => setStep("done")}
          />
        )}
        {step === "done" && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-sm text-muted-foreground"
          >
            All set. <a className="text-primary hover:underline" href="/auth/login">Sign in to continue</a>.
          </motion.p>
        )}
      </CardContent>
    </Card>
  );
}

function OtpStep({
  userId,
  onSuccess,
}: {
  userId: string;
  onSuccess: () => void;
}) {
  const { push } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [requesting, setRequesting] = useState(false);

  type FormValues = z.infer<typeof otpSchema>;
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(otpSchema) });

  async function requestCode() {
    setRequesting(true);
    try {
      await api("/auth/tenant/otp/request", {
        method: "POST",
        body: { user_id: userId },
      });
      push({ kind: "info", message: "Code sent. Check your messages." });
    } catch (e) {
      const msg =
        e instanceof ApiError ? e.message : "Could not send code. Try again.";
      push({ kind: "error", message: msg });
    } finally {
      setRequesting(false);
    }
  }

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    try {
      await api("/auth/tenant/otp/verify", {
        method: "POST",
        body: { user_id: userId, code: values.code },
      });
      onSuccess();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Code rejected.";
      push({ kind: "error", message: msg });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      aria-label="otp-form"
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4"
      noValidate
    >
      <div className="space-y-2">
        <Label htmlFor="code">6-digit code</Label>
        <Input
          id="code"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          {...register("code")}
          aria-invalid={!!errors.code}
        />
        {errors.code && (
          <p role="alert" className="text-sm text-destructive">
            {errors.code.message}
          </p>
        )}
      </div>
      <div className="flex items-center justify-between gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={requestCode}
          disabled={requesting}
        >
          {requesting ? "Sending…" : "Send code"}
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Verifying…" : "Verify"}
        </Button>
      </div>
    </form>
  );
}

function PasswordStep({
  userId,
  onSuccess,
}: {
  userId: string;
  onSuccess: () => void;
}) {
  const { push } = useToast();
  const [submitting, setSubmitting] = useState(false);

  type FormValues = z.infer<typeof passwordSchema>;
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(passwordSchema) });

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    try {
      await api("/auth/tenant/set-password", {
        method: "POST",
        body: { user_id: userId, password: values.password },
      });
      push({ kind: "success", message: "Password set. You can sign in." });
      onSuccess();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Could not set password.";
      push({ kind: "error", message: msg });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      aria-label="set-password-form"
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4"
      noValidate
    >
      <div className="space-y-2">
        <Label htmlFor="password">New password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
          aria-invalid={!!errors.password}
        />
        {errors.password && (
          <p role="alert" className="text-sm text-destructive">
            {errors.password.message}
          </p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirm">Confirm password</Label>
        <Input
          id="confirm"
          type="password"
          autoComplete="new-password"
          {...register("confirm")}
          aria-invalid={!!errors.confirm}
        />
        {errors.confirm && (
          <p role="alert" className="text-sm text-destructive">
            {errors.confirm.message}
          </p>
        )}
      </div>
      <Button className="w-full" disabled={submitting}>
        {submitting ? "Saving…" : "Save password"}
      </Button>
    </form>
  );
}
