"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { formatKES, formatDate } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

interface Installment {
  date: string;
  amount: string | number;
  paid_payment_id?: string | null;
}

interface PlanOut {
  id: string;
  invoice_id: string;
  tenant_id: string;
  status: "pending" | "approved" | "rejected" | "completed" | "defaulted";
  schedule: Installment[];
  created_at: string;
}

const TABS = [
  { id: "pending", label: "Pending" },
  { id: "approved", label: "Active" },
  { id: "defaulted", label: "Defaulted" },
] as const;

export default function PlansPage() {
  const qc = useQueryClient();
  const { push } = useToast();
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("pending");

  const list = useQuery({
    queryKey: ["plans", tab],
    queryFn: () => api<PlanOut[]>(`/admin/plans?status=${tab}`),
  });

  const decide = useMutation({
    mutationFn: (vars: {
      planId: string;
      action: "approve" | "reject" | "counter";
      counter_schedule?: Installment[];
    }) =>
      api(`/admin/plans/${vars.planId}/decision`, {
        method: "POST",
        body: {
          action: vars.action,
          counter_schedule: vars.counter_schedule,
        },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plans"] });
      push({ kind: "success", message: "Decision saved" });
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Could not save decision",
      }),
  });

  return (
    <>
      <PageHeader title="Payment plans" />

      <div role="tablist" className="mb-4 flex gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-md border px-3 py-1 text-sm transition-colors ${
              tab === t.id
                ? "border-primary bg-primary text-primary-foreground"
                : "hover:bg-muted"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {list.isLoading ? (
        <Skeleton className="h-32" />
      ) : (list.data?.length ?? 0) === 0 ? (
        <p className="text-sm text-muted-foreground">No plans here.</p>
      ) : (
        <div className="space-y-3">
          {list.data!.map((p) => (
            <Card key={p.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">Plan {p.id.slice(0, 8)}…</p>
                    <p className="text-sm text-muted-foreground">
                      Invoice {p.invoice_id.slice(0, 8)}… · created {formatDate(p.created_at)}
                    </p>
                  </div>
                  <Badge
                    variant={
                      p.status === "approved"
                        ? "paid"
                        : p.status === "defaulted"
                        ? "overdue"
                        : "secondary"
                    }
                  >
                    {p.status}
                  </Badge>
                </div>
                <ul className="mt-3 grid gap-1 text-sm md:grid-cols-2">
                  {p.schedule.map((inst, idx) => (
                    <li key={idx} className="flex justify-between border-b py-1">
                      <span>{formatDate(inst.date)}</span>
                      <span className="tabular-nums">{formatKES(inst.amount)}</span>
                    </li>
                  ))}
                </ul>
                {p.status === "pending" && (
                  <div className="mt-3 flex gap-2">
                    <Button
                      size="sm"
                      onClick={() =>
                        decide.mutate({ planId: p.id, action: "approve" })
                      }
                      disabled={decide.isPending}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        decide.mutate({ planId: p.id, action: "reject" })
                      }
                      disabled={decide.isPending}
                    >
                      Reject
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
