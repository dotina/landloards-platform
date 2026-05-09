import type { ReactNode } from "react";
import { TenantBottomNav, TenantSidebar } from "@/components/tenant/nav";
import { DashboardTopbar } from "@/components/dashboard/topbar";

export default function TenantLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-muted/30">
      <TenantSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <DashboardTopbar />
        <main className="flex-1 overflow-y-auto">
          <div className="container max-w-3xl py-6 md:py-10">{children}</div>
        </main>
        <TenantBottomNav />
      </div>
    </div>
  );
}
