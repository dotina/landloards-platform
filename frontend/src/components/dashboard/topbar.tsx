"use client";

import { useQuery } from "@tanstack/react-query";
import { whoami, logout } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export function DashboardTopbar() {
  const { data } = useQuery({ queryKey: ["whoami"], queryFn: whoami });
  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-4">
      <span className="text-sm text-muted-foreground">
        {data?.name ? `Hi, ${data.name}` : "Loading…"}
      </span>
      <Button
        variant="ghost"
        size="sm"
        onClick={async () => {
          await logout();
          window.location.href = "/auth/login";
        }}
      >
        Sign out
      </Button>
    </header>
  );
}
