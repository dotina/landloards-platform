"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { formatKES, formatDate } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

interface InvoiceOut {
  id: string;
  status: string;
  amount: string | number;
  late_fee_accrued: string | number;
  period_start: string;
}
interface PlanOut {
  id: string;
  invoice_id: string;
  status: string;
  schedule: { date: string; amount: string | number }[];
  created_at: string;
}

const PLAN_ELIGIBLE = new Set(["partial", "overdue"]);

export default function TenantPlanPage() {
  const qc = useQueryClient();
  const { push } = useToast();

  const invoices = useQuery({
    queryKey: ["my-invoices"],
    queryFn: () => api<InvoiceOut[]>("/tenant/invoices"),
  });
  const plans = useQuery({
    queryKey: ["my-plans"],
    queryFn: () => api<PlanOut[]>("/plans/me"),
  });

  const eligible = (invoices.data ?? []).filter((i) =>
    PLAN_ELIGIBLE.has(i.status)
  );
  const [invoiceId, setInvoiceId] = useState<string>("");
  const [rows, setRows] = useState<{ date: string; amount: string }[]>([
    { date: "", amount: "" },
  ]);

  const submit = useMutation({
    mutationFn: () =>
      api("/plans", {
        method: "POST",
        body: {
          invoice_id: invoiceId,
          schedule: rows.map((r) => ({ date: r.date, amount: r.amount })),
        },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-plans"] });
      push({ kind: "success", message: "Plan submitted" });
      setInvoiceId("");
      setRows([{ date: "", amount: "" }]);
    },
    onError: (e: unknown) =>
      push({
        kind: "error",
        message: e instanceof ApiError ? e.message : "Could not submit plan",
      }),
  });

  return (
    <>
      <PageHeader
        title="Payment plan"
        description="Spread an overdue invoice across smaller installments."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Active &amp; past plans</CardTitle>
        </CardHeader>
        <CardContent>
          {plans.isLoading ? (
            <Skeleton className="h-16" />
          ) : (plans.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">No plans yet.</p>
          ) : (
            <ul className="space-y-2">
              {plans.data!.map((p) => (
                <li key={p.id} className="rounded-md border p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span>Plan {p.id.slice(0, 8)}…</span>
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
                  <ul className="mt-2 grid gap-1 md:grid-cols-2">
                    {p.schedule.map((s, idx) => (
                      <li
                        key={idx}
                        className="flex justify-between border-b py-1 text-xs"
                      >
                        <span>{formatDate(s.date)}</span>
                        <span className="tabular-nums">{formatKES(s.amount)}</span>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {eligible.length > 0 && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-base">Request a new plan</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              aria-label="plan-form"
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!invoiceId || rows.some((r) => !r.date || !r.amount)) return;
                submit.mutate();
              }}
            >
              <div className="space-y-1">
                <Label htmlFor="inv">Invoice</Label>
                <select
                  id="inv"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={invoiceId}
                  onChange={(e) => setInvoiceId(e.target.value)}
                >
                  <option value="">Select an invoice…</option>
                  {eligible.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.period_start} — {formatKES(
                        Number(i.amount) + Number(i.late_fee_accrued)
                      )} ({i.status})
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>Installments</Label>
                {rows.map((r, idx) => (
                  <div key={idx} className="grid grid-cols-2 gap-2">
                    <Input
                      type="date"
                      aria-label={`installment date ${idx + 1}`}
                      value={r.date}
                      onChange={(e) =>
                        setRows((rs) =>
                          rs.map((row, i) =>
                            i === idx ? { ...row, date: e.target.value } : row
                          )
                        )
                      }
                    />
                    <Input
                      type="number"
                      aria-label={`installment amount ${idx + 1}`}
                      placeholder="Amount"
                      min="1"
                      value={r.amount}
                      onChange={(e) =>
                        setRows((rs) =>
                          rs.map((row, i) =>
                            i === idx ? { ...row, amount: e.target.value } : row
                          )
                        )
                      }
                    />
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setRows((rs) =>
                      rs.length < 12 ? [...rs, { date: "", amount: "" }] : rs
                    )
                  }
                >
                  Add installment
                </Button>
              </div>
              <Button type="submit" disabled={submit.isPending}>
                {submit.isPending ? "Submitting…" : "Submit plan"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}
    </>
  );
}
