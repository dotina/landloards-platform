"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKES, formatDate } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";

interface UnitOut {
  id: string;
  label: string;
  rent_amount: string | number;
  due_day_of_month: number;
  status: "vacant" | "occupied";
}

interface LeaseOut {
  id: string;
  tenant_id: string;
  unit_id: string;
  start_date: string;
  end_date: string;
  rent_amount: string | number;
  status: "active" | "ended";
}

export default function UnitDetailPage() {
  const { id } = useParams<{ id: string }>();

  const unit = useQuery({
    queryKey: ["unit", id],
    queryFn: () => api<UnitOut>(`/units/${id}`),
  });
  const leases = useQuery({
    queryKey: ["leases", { unit: id }],
    queryFn: () => api<LeaseOut[]>(`/leases?unit_id=${id}`),
  });

  return (
    <>
      <PageHeader
        title={unit.data ? `Unit ${unit.data.label}` : "Unit"}
        description={
          unit.data ? `${formatKES(unit.data.rent_amount)} · due day ${unit.data.due_day_of_month}` : undefined
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Lease history</CardTitle>
        </CardHeader>
        <CardContent>
          {leases.isLoading ? (
            <Skeleton className="h-24" />
          ) : (leases.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">No leases yet.</p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Lease</TH>
                  <TH>Tenant</TH>
                  <TH>Start</TH>
                  <TH>End</TH>
                  <TH>Rent</TH>
                  <TH>Status</TH>
                </TR>
              </THead>
              <TBody>
                {leases.data!.map((l) => (
                  <TR key={l.id}>
                    <TD>{l.id.slice(0, 8)}…</TD>
                    <TD>{l.tenant_id.slice(0, 8)}…</TD>
                    <TD>{formatDate(l.start_date)}</TD>
                    <TD>{formatDate(l.end_date)}</TD>
                    <TD className="tabular-nums">{formatKES(l.rent_amount)}</TD>
                    <TD>
                      <Badge
                        variant={l.status === "active" ? "default" : "secondary"}
                      >
                        {l.status}
                      </Badge>
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
