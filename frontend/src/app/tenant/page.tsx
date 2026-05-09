"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKES, formatDate } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface InvoiceOut {
  id: string;
  status: string;
  amount: string | number;
  late_fee_accrued: string | number;
  period_start: string;
  due_date: string;
}
interface PaymentOut {
  id: string;
  status: string;
  amount: string | number;
  channel: string;
  created_at: string;
}
interface PlanOut {
  id: string;
  invoice_id: string;
  status: string;
  schedule: { date: string; amount: string | number }[];
}

function num(v: string | number): number {
  return typeof v === "number" ? v : Number(v) || 0;
}

export default function TenantHome() {
  const invoices = useQuery({
    queryKey: ["my-invoices"],
    queryFn: () => api<InvoiceOut[]>("/tenant/invoices"),
  });
  const payments = useQuery({
    queryKey: ["my-payments"],
    queryFn: () => api<PaymentOut[]>("/tenant/payments"),
  });
  const plans = useQuery({
    queryKey: ["my-plans"],
    queryFn: () => api<PlanOut[]>("/plans/me"),
  });

  const due = (invoices.data ?? [])
    .filter((i) => ["open", "partial", "overdue"].includes(i.status))
    .reduce((s, i) => s + num(i.amount) + num(i.late_fee_accrued), 0);

  const activePlan = (plans.data ?? []).find(
    (p) => p.status === "approved" || p.status === "pending"
  );

  return (
    <>
      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle className="text-sm text-muted-foreground font-normal">
            Total due
          </CardTitle>
        </CardHeader>
        <CardContent>
          {invoices.isLoading ? (
            <Skeleton className="h-10 w-40" />
          ) : (
            <p className="text-3xl font-semibold tabular-nums">
              {formatKES(due)}
            </p>
          )}
          <div className="mt-4 flex gap-2">
            <Link href="/tenant/pay">
              <Button size="lg" disabled={due <= 0}>
                Pay now
              </Button>
            </Link>
            <Link href="/tenant/history">
              <Button size="lg" variant="outline">
                View history
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {activePlan && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-base">Payment plan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              Status:{" "}
              <Badge
                variant={activePlan.status === "approved" ? "paid" : "secondary"}
              >
                {activePlan.status}
              </Badge>
            </p>
            <p>{activePlan.schedule.length} installments scheduled.</p>
            <Link className="text-primary hover:underline" href="/tenant/plan">
              View plan →
            </Link>
          </CardContent>
        </Card>
      )}

      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Recent activity</CardTitle>
        </CardHeader>
        <CardContent>
          {payments.isLoading ? (
            <Skeleton className="h-16" />
          ) : (payments.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">No payments yet.</p>
          ) : (
            <ul className="divide-y">
              {payments.data!.slice(0, 5).map((p) => (
                <li key={p.id} className="flex items-center justify-between py-2 text-sm">
                  <span>{formatDate(p.created_at)}</span>
                  <span className="flex items-center gap-3">
                    <Badge variant={p.status === "success" ? "paid" : "secondary"}>
                      {p.status}
                    </Badge>
                    <span className="tabular-nums">{formatKES(p.amount)}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  );
}
