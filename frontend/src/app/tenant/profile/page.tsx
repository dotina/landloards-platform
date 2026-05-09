"use client";

import { useEffect, useState, type ChangeEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

interface NextOfKin {
  name: string;
  phone: string;
  relationship: string;
}
interface TenantProfile {
  employer: string | null;
  next_of_kin: NextOfKin | null;
  kyc_status: "pending" | "approved" | "rejected" | "not_uploaded";
}

export default function TenantProfilePage() {
  const qc = useQueryClient();
  const { push } = useToast();

  const profile = useQuery({
    queryKey: ["tenant-me"],
    queryFn: () => api<TenantProfile>("/tenant/me"),
  });

  const [form, setForm] = useState<{
    employer: string;
    nok_name: string;
    nok_phone: string;
    nok_rel: string;
  }>({
    employer: "",
    nok_name: "",
    nok_phone: "",
    nok_rel: "",
  });

  useEffect(() => {
    if (!profile.data) return;
    setForm({
      employer: profile.data.employer ?? "",
      nok_name: profile.data.next_of_kin?.name ?? "",
      nok_phone: profile.data.next_of_kin?.phone ?? "",
      nok_rel: profile.data.next_of_kin?.relationship ?? "",
    });
  }, [profile.data]);

  const update = useMutation({
    mutationFn: () =>
      api("/tenant/me", {
        method: "PATCH",
        body: {
          employer: form.employer || null,
          next_of_kin:
            form.nok_name && form.nok_phone && form.nok_rel
              ? {
                  name: form.nok_name,
                  phone: form.nok_phone,
                  relationship: form.nok_rel,
                }
              : null,
        },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenant-me"] });
      push({ kind: "success", message: "Profile saved" });
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Could not save",
      }),
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api("/tenant/kyc/upload", { method: "POST", body: fd });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenant-me"] });
      push({
        kind: "success",
        message: "KYC document uploaded — awaiting review.",
      });
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Upload failed",
      }),
  });

  return (
    <>
      <PageHeader
        title="Profile"
        description="KYC, employer, and next of kin."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">KYC</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {profile.isLoading ? (
            <Skeleton className="h-10" />
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-sm">Status</span>
              <Badge
                variant={
                  profile.data?.kyc_status === "approved"
                    ? "paid"
                    : profile.data?.kyc_status === "rejected"
                    ? "overdue"
                    : "secondary"
                }
              >
                {profile.data?.kyc_status ?? "—"}
              </Badge>
            </div>
          )}
          <div className="space-y-1">
            <Label htmlFor="kyc">Upload ID / passport / KRA PIN (≤ 10 MB)</Label>
            <Input
              id="kyc"
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              onChange={(e: ChangeEvent<HTMLInputElement>) => {
                const f = e.target.files?.[0];
                if (f) upload.mutate(f);
              }}
            />
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Employer &amp; next of kin</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            aria-label="profile-form"
            className="grid gap-3 md:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              update.mutate();
            }}
          >
            <Field
              id="employer"
              label="Employer"
              value={form.employer}
              onChange={(v) => setForm((f) => ({ ...f, employer: v }))}
            />
            <Field
              id="nok_name"
              label="Next of kin name"
              value={form.nok_name}
              onChange={(v) => setForm((f) => ({ ...f, nok_name: v }))}
            />
            <Field
              id="nok_phone"
              label="Next of kin phone"
              value={form.nok_phone}
              onChange={(v) => setForm((f) => ({ ...f, nok_phone: v }))}
            />
            <Field
              id="nok_rel"
              label="Relationship"
              value={form.nok_rel}
              onChange={(v) => setForm((f) => ({ ...f, nok_rel: v }))}
            />
            <div className="md:col-span-2">
              <Button type="submit" disabled={update.isPending}>
                {update.isPending ? "Saving…" : "Save"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
