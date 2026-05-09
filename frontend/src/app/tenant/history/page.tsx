"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate, formatKES } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";

interface PaymentOut {
  id: string;
  status: string;
  amount: string | number;
  channel: string;
  mpesa_receipt: string | null;
  created_at: string;
}

export default function TenantHistoryPage() {
  const list = useQuery({
    queryKey: ["my-payments"],
    queryFn: () => api<PaymentOut[]>("/tenant/payments"),
  });

  return (
    <>
      <PageHeader
        title="Payment history"
        actions={
          <Button
            variant="outline"
            onClick={() =>
              window.open("/api/tenant/me/statement.pdf", "_blank")
            }
          >
            Download statement
          </Button>
        }
      />
      <Card>
        <CardContent className="p-0">
          {list.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-24" />
            </div>
          ) : (list.data?.length ?? 0) === 0 ? (
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
                {list.data!.map((p) => (
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
