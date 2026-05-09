"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKES } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

interface PropertyOut {
  id: string;
  name: string;
}
interface UnitOut {
  id: string;
  status: string;
  property_id: string;
  rent_amount: string | number;
}
interface InvoiceOut {
  id: string;
  status: string;
  amount: string | number;
  late_fee_accrued: string | number;
  tenant_id?: string;
  lease_id: string;
}
interface PaymentOut {
  id: string;
  status: string;
  amount: string | number;
  channel: string;
  created_at?: string;
}

function num(v: string | number): number {
  return typeof v === "number" ? v : Number(v) || 0;
}

export default function DashboardOverview() {
  const properties = useQuery({
    queryKey: ["properties"],
    queryFn: () => api<PropertyOut[]>("/properties"),
  });
  const invoices = useQuery({
    queryKey: ["invoices", "all"],
    queryFn: () => api<InvoiceOut[]>("/invoices"),
  });
  const payments = useQuery({
    queryKey: ["payments", "all"],
    queryFn: () => api<PaymentOut[]>("/admin/payments"),
  });

  const collected = (payments.data ?? [])
    .filter((p) => p.status === "success")
    .reduce((s, p) => s + num(p.amount), 0);
  const outstanding = (invoices.data ?? [])
    .filter((i) => ["open", "partial", "overdue"].includes(i.status))
    .reduce((s, i) => s + num(i.amount) + num(i.late_fee_accrued), 0);
  const defaulters = (invoices.data ?? []).filter(
    (i) => i.status === "overdue" || i.status === "defaulted"
  );

  return (
    <>
      <PageHeader
        title="Overview"
        description="A snapshot of properties, collections, and outstanding rent."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KPICard
          label="Properties"
          value={properties.data?.length ?? 0}
          loading={properties.isLoading}
        />
        <KPICard
          label="Collected (this view)"
          value={formatKES(collected)}
          loading={payments.isLoading}
        />
        <KPICard
          label="Outstanding"
          value={formatKES(outstanding)}
          loading={invoices.isLoading}
        />
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Defaulters</CardTitle>
        </CardHeader>
        <CardContent>
          {invoices.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : defaulters.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No overdue invoices. Nice work.
            </p>
          ) : (
            <ul className="divide-y" aria-label="defaulters">
              {defaulters.map((inv) => (
                <li
                  key={inv.id}
                  className="flex items-center justify-between py-2 text-sm"
                >
                  <span>Invoice {inv.id.slice(0, 8)}…</span>
                  <span className="flex items-center gap-3">
                    <Badge variant={inv.status === "overdue" ? "overdue" : "destructive"}>
                      {inv.status}
                    </Badge>
                    <span className="tabular-nums">
                      {formatKES(num(inv.amount) + num(inv.late_fee_accrued))}
                    </span>
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

function KPICard({
  label,
  value,
  loading,
}: {
  label: string;
  value: string | number;
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground font-medium">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-7 w-32" />
        ) : (
          <p className="text-2xl font-semibold tabular-nums">{value}</p>
        )}
      </CardContent>
    </Card>
  );
}
