"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface NotificationOut {
  id: string;
  channel: "sms" | "email";
  template: string;
  status: string;
  body: string;
  created_at: string;
}

export default function TenantInboxPage() {
  const list = useQuery({
    queryKey: ["my-notifications"],
    queryFn: () => api<NotificationOut[]>("/tenant/notifications"),
  });

  return (
    <>
      <PageHeader title="Inbox" description="Your messages from your landlord." />
      {list.isLoading ? (
        <Skeleton className="h-32" />
      ) : (list.data?.length ?? 0) === 0 ? (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            No messages yet.
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-3" aria-label="messages">
          {list.data!.map((n) => (
            <Card key={n.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <span className="text-xs text-muted-foreground">
                    {formatDate(n.created_at)} · {n.channel} · {n.template}
                  </span>
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
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm">{n.body}</p>
              </CardContent>
            </Card>
          ))}
        </ul>
      )}
    </>
  );
}
