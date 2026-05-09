"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";

interface NotificationLogOut {
  id: string;
  channel: "sms" | "email";
  recipient: string;
  template: string;
  status: "queued" | "sent" | "delivered" | "failed";
  created_at: string;
  failure_reason?: string | null;
}

export default function NotificationsPage() {
  const list = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api<NotificationLogOut[]>("/admin/notifications"),
  });

  return (
    <>
      <PageHeader
        title="Notifications"
        description="Outbound SMS and email log."
      />
      <Card>
        <CardContent className="p-0">
          {list.isLoading ? (
            <div className="p-6">
              <Skeleton className="h-24" />
            </div>
          ) : (list.data?.length ?? 0) === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              No notifications yet.
            </p>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>When</TH>
                  <TH>Channel</TH>
                  <TH>Recipient</TH>
                  <TH>Template</TH>
                  <TH>Status</TH>
                </TR>
              </THead>
              <TBody>
                {list.data!.map((n) => (
                  <TR key={n.id}>
                    <TD>{formatDate(n.created_at)}</TD>
                    <TD>{n.channel}</TD>
                    <TD>{n.recipient}</TD>
                    <TD>{n.template}</TD>
                    <TD>
                      <Badge
                        variant={
                          n.status === "delivered" || n.status === "sent"
                            ? "paid"
                            : n.status === "failed"
                            ? "overdue"
                            : "secondary"
                        }
                      >
                        {n.status}
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
