"use client";

import { useQuery } from "@tanstack/react-query";
import { whoami } from "@/lib/auth";
import { PageHeader } from "@/components/dashboard/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function SettingsPage() {
  const me = useQuery({ queryKey: ["whoami"], queryFn: whoami });

  return (
    <>
      <PageHeader
        title="Settings"
        description="Profile, M-Pesa, and notification preferences."
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Profile</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {me.isLoading ? (
              <Skeleton className="h-16" />
            ) : me.data ? (
              <ul className="space-y-1">
                <li>
                  <span className="text-muted-foreground">Name:</span>{" "}
                  {me.data.name}
                </li>
                <li>
                  <span className="text-muted-foreground">Email:</span>{" "}
                  {me.data.email ?? "—"}
                </li>
                <li>
                  <span className="text-muted-foreground">Phone:</span>{" "}
                  {me.data.phone}
                </li>
                <li>
                  <span className="text-muted-foreground">Role:</span>{" "}
                  {me.data.role}
                </li>
              </ul>
            ) : (
              <p className="text-muted-foreground">Not signed in.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">M-Pesa</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Configured server-side. Talk to support to swap your paybill.
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Reminders &amp; late fees</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Default cadence: T-3, T-0, T+3, T+7, T+14. Late-fee rule is
            configured per lease.
          </CardContent>
        </Card>
      </div>
    </>
  );
}
