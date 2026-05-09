"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate, formatKES } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface LeaseOut {
  id: string;
  unit_id: string;
  start_date: string;
  end_date: string;
  rent_amount: string | number;
  deposit_amount: string | number;
  status: "active" | "ended";
}

export default function TenantLeasePage() {
  const list = useQuery({
    queryKey: ["my-leases"],
    queryFn: () => api<LeaseOut[]>("/tenant/leases"),
  });
  const active = (list.data ?? []).find((l) => l.status === "active");

  return (
    <>
      <PageHeader title="Lease" description="Read-only view of your tenancy." />

      {list.isLoading ? (
        <Skeleton className="h-32" />
      ) : !active ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No active lease on file.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="space-y-2 p-6 text-sm">
            <p className="flex items-center justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant="paid">{active.status}</Badge>
            </p>
            <p className="flex items-center justify-between">
              <span className="text-muted-foreground">From</span>
              <span>{formatDate(active.start_date)}</span>
            </p>
            <p className="flex items-center justify-between">
              <span className="text-muted-foreground">To</span>
              <span>{formatDate(active.end_date)}</span>
            </p>
            <p className="flex items-center justify-between">
              <span className="text-muted-foreground">Rent</span>
              <span className="tabular-nums">{formatKES(active.rent_amount)}</span>
            </p>
            <p className="flex items-center justify-between">
              <span className="text-muted-foreground">Deposit</span>
              <span className="tabular-nums">{formatKES(active.deposit_amount)}</span>
            </p>
          </CardContent>
        </Card>
      )}
    </>
  );
}
