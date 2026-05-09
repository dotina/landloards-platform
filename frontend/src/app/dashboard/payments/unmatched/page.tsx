"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { formatKES, formatDate } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";

interface UnmatchedOut {
  id: string;
  amount: string | number;
  bill_ref: string | null;
  msisdn: string;
  trans_id: string;
  created_at: string;
}

export default function UnmatchedAllocationPage() {
  const qc = useQueryClient();
  const { push } = useToast();
  const list = useQuery({
    queryKey: ["unmatched"],
    queryFn: () => api<UnmatchedOut[]>("/admin/payments/c2b/unmatched"),
  });
  const [draft, setDraft] = useState<Record<string, { tenantCode: string }>>({});

  const allocate = useMutation({
    mutationFn: (vars: { id: string; tenantCode: string }) =>
      api(`/admin/payments/c2b/unmatched/${vars.id}/allocate`, {
        method: "POST",
        body: { tenant_code: vars.tenantCode },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["unmatched"] });
      qc.invalidateQueries({ queryKey: ["admin-payments"] });
      push({ kind: "success", message: "Payment allocated" });
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Could not allocate",
      }),
  });

  return (
    <>
      <PageHeader
        title="Unmatched payments"
        description="C2B payments where the BillRefNumber didn't match a tenant code."
      />
      <Card>
        <CardContent className="p-0">
          {list.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-24" />
            </div>
          ) : (list.data?.length ?? 0) === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              All clear — nothing to allocate.
            </p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>When</TH>
                  <TH>Amount</TH>
                  <TH>Phone</TH>
                  <TH>BillRef</TH>
                  <TH>M-Pesa</TH>
                  <TH>Allocate</TH>
                </TR>
              </THead>
              <TBody>
                {list.data!.map((u) => {
                  const value = draft[u.id]?.tenantCode ?? "";
                  return (
                    <TR key={u.id}>
                      <TD>{formatDate(u.created_at)}</TD>
                      <TD className="tabular-nums">{formatKES(u.amount)}</TD>
                      <TD>{u.msisdn}</TD>
                      <TD>{u.bill_ref ?? "—"}</TD>
                      <TD>{u.trans_id}</TD>
                      <TD>
                        <form
                          aria-label="allocate-form"
                          className="flex items-end gap-2"
                          onSubmit={(e) => {
                            e.preventDefault();
                            if (!value.trim()) return;
                            allocate.mutate({
                              id: u.id,
                              tenantCode: value.trim().toUpperCase(),
                            });
                          }}
                        >
                          <div className="space-y-1">
                            <Label htmlFor={`code-${u.id}`} className="sr-only">
                              Tenant code
                            </Label>
                            <Input
                              id={`code-${u.id}`}
                              placeholder="XK4P9R"
                              value={value}
                              onChange={(e) =>
                                setDraft((d) => ({
                                  ...d,
                                  [u.id]: { tenantCode: e.target.value },
                                }))
                              }
                            />
                          </div>
                          <Button size="sm" disabled={allocate.isPending}>
                            Apply
                          </Button>
                        </form>
                      </TD>
                    </TR>
                  );
                })}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
