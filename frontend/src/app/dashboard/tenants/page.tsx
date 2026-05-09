"use client";

import { useState } from "react";
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
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";

interface AdminTenantOut {
  id: string;
  user_id: string;
  name: string;
  phone: string;
  kyc_status: "pending" | "approved" | "rejected" | "not_uploaded";
  tenant_code: string | null;
}

export default function TenantsPage() {
  const qc = useQueryClient();
  const { push } = useToast();
  const list = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () => api<AdminTenantOut[]>("/admin/tenants"),
  });

  const [inviting, setInviting] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const invite = useMutation({
    mutationFn: () =>
      api("/landlord/tenants/invite", {
        method: "POST",
        body: { name, phone, email: email || null },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-tenants"] });
      setInviting(false);
      setName("");
      setPhone("");
      setEmail("");
      push({ kind: "success", message: "Tenant invited" });
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Could not invite",
      }),
  });

  const decide = useMutation({
    mutationFn: (vars: {
      tenantId: string;
      action: "approve" | "reject";
      reason?: string;
    }) =>
      api(`/admin/tenants/${vars.tenantId}/kyc/decision`, {
        method: "POST",
        body: { action: vars.action, reason: vars.reason },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-tenants"] });
      push({ kind: "success", message: "KYC decision saved" });
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Could not save decision",
      }),
  });

  return (
    <>
      <PageHeader
        title="Tenants"
        actions={
          <Button onClick={() => setInviting((v) => !v)}>
            {inviting ? "Cancel" : "Invite tenant"}
          </Button>
        }
      />

      {inviting && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">Invite tenant</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              aria-label="invite-form"
              className="grid gap-3 md:grid-cols-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!name || !phone) return;
                invite.mutate();
              }}
            >
              <div className="space-y-1">
                <Label htmlFor="t-name">Name</Label>
                <Input
                  id="t-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="t-phone">Phone (E.164)</Label>
                <Input
                  id="t-phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="t-email">Email (optional)</Label>
                <Input
                  id="t-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="md:col-span-3">
                <Button type="submit" disabled={invite.isPending}>
                  {invite.isPending ? "Sending…" : "Send invite"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {list.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-24" />
            </div>
          ) : (list.data?.length ?? 0) === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              No tenants yet. Invite your first one.
            </p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Name</TH>
                  <TH>Phone</TH>
                  <TH>Tenant code</TH>
                  <TH>KYC</TH>
                  <TH className="text-right">Actions</TH>
                </TR>
              </THead>
              <TBody>
                {list.data!.map((t) => (
                  <TR key={t.id}>
                    <TD className="font-medium">{t.name}</TD>
                    <TD>{t.phone}</TD>
                    <TD>{t.tenant_code ?? "—"}</TD>
                    <TD>
                      <Badge
                        variant={
                          t.kyc_status === "approved"
                            ? "paid"
                            : t.kyc_status === "rejected"
                            ? "overdue"
                            : "secondary"
                        }
                      >
                        {t.kyc_status}
                      </Badge>
                    </TD>
                    <TD className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            decide.mutate({
                              tenantId: t.id,
                              action: "approve",
                            })
                          }
                          disabled={
                            t.kyc_status === "approved" || decide.isPending
                          }
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            const reason =
                              window.prompt("Reason for rejection?") ?? "";
                            if (reason)
                              decide.mutate({
                                tenantId: t.id,
                                action: "reject",
                                reason,
                              });
                          }}
                          disabled={
                            t.kyc_status === "rejected" || decide.isPending
                          }
                        >
                          Reject
                        </Button>
                      </div>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
