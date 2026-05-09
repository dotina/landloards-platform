"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatKES, formatDate } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";

interface PaymentOut {
  id: string;
  status: string;
  amount: string | number;
  channel: string;
  mpesa_receipt: string | null;
  created_at: string;
}
interface UnmatchedOut {
  id: string;
  amount: string | number;
  bill_ref: string | null;
  msisdn: string;
  trans_id: string;
  created_at: string;
}

export default function PaymentsPage() {
  const payments = useQuery({
    queryKey: ["admin-payments"],
    queryFn: () => api<PaymentOut[]>("/admin/payments"),
  });
  const unmatched = useQuery({
    queryKey: ["unmatched"],
    queryFn: () => api<UnmatchedOut[]>("/admin/payments/c2b/unmatched"),
  });

  return (
    <>
      <PageHeader title="Payments" />

      {(unmatched.data?.length ?? 0) > 0 && (
        <Card className="mb-6 border-overdue-500/50">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span>
                Unmatched M-Pesa payments ({unmatched.data?.length ?? 0})
              </span>
              <Link
                className="text-sm text-primary hover:underline"
                href="/dashboard/payments/unmatched"
              >
                Allocate →
              </Link>
            </CardTitle>
          </CardHeader>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {payments.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-24" />
            </div>
          ) : (payments.data?.length ?? 0) === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">No payments yet.</p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>When</TH>
                  <TH>Amount</TH>
                  <TH>Channel</TH>
                  <TH>Receipt</TH>
                  <TH>Status</TH>
                  <TH></TH>
                </TR>
              </THead>
              <TBody>
                {payments.data!.map((p) => (
                  <TR key={p.id}>
                    <TD>{formatDate(p.created_at)}</TD>
                    <TD className="tabular-nums">{formatKES(p.amount)}</TD>
                    <TD>{p.channel}</TD>
                    <TD>{p.mpesa_receipt ?? "—"}</TD>
                    <TD>
                      <Badge
                        variant={
                          p.status === "success"
                            ? "paid"
                            : p.status === "failed"
                            ? "overdue"
                            : "secondary"
                        }
                      >
                        {p.status}
                      </Badge>
                    </TD>
                    <TD className="text-right">
                      {p.status === "success" && (
                        <a
                          className="text-sm text-primary hover:underline"
                          href={`/api/payments/${p.id}/receipt.pdf`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Receipt
                        </a>
                      )}
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
