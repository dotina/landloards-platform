"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKES, formatDate } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";

interface InvoiceOut {
  id: string;
  status: string;
  amount: string | number;
  late_fee_accrued: string | number;
  period_start: string;
  due_date: string;
  lease_id: string;
}

const STATUSES = [
  "all",
  "open",
  "partial",
  "paid",
  "overdue",
  "on_pay_plan",
  "defaulted",
  "written_off",
] as const;

function statusVariant(s: string) {
  switch (s) {
    case "paid":
      return "paid" as const;
    case "open":
    case "partial":
      return "due" as const;
    case "overdue":
    case "defaulted":
      return "overdue" as const;
    default:
      return "secondary" as const;
  }
}

export default function InvoicesPage() {
  const [filter, setFilter] = useState<(typeof STATUSES)[number]>("all");
  const list = useQuery({
    queryKey: ["invoices"],
    queryFn: () => api<InvoiceOut[]>("/invoices"),
  });

  const filtered =
    filter === "all"
      ? list.data ?? []
      : (list.data ?? []).filter((i) => i.status === filter);

  return (
    <>
      <PageHeader title="Invoices" />

      <div className="mb-4 flex flex-wrap gap-2" role="tablist">
        {STATUSES.map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={filter === s}
            onClick={() => setFilter(s)}
            className={`rounded-md border px-3 py-1 text-sm transition-colors ${
              filter === s
                ? "border-primary bg-primary text-primary-foreground"
                : "hover:bg-muted"
            }`}
          >
            {s.replaceAll("_", " ")}
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          {list.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-24" />
            </div>
          ) : filtered.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              No invoices match.
            </p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Invoice</TH>
                  <TH>Period</TH>
                  <TH>Due</TH>
                  <TH>Amount</TH>
                  <TH>Late fee</TH>
                  <TH>Status</TH>
                </TR>
              </THead>
              <TBody>
                {filtered.map((i) => (
                  <TR key={i.id}>
                    <TD>{i.id.slice(0, 8)}…</TD>
                    <TD>{formatDate(i.period_start)}</TD>
                    <TD>{formatDate(i.due_date)}</TD>
                    <TD className="tabular-nums">{formatKES(i.amount)}</TD>
                    <TD className="tabular-nums">
                      {formatKES(i.late_fee_accrued)}
                    </TD>
                    <TD>
                      <Badge variant={statusVariant(i.status)}>
                        {i.status.replaceAll("_", " ")}
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
