"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, CreditCard, Receipt, FileText, CalendarRange, User, Bell } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV: { href: string; label: string; icon: typeof Home }[] = [
  { href: "/tenant", label: "Home", icon: Home },
  { href: "/tenant/pay", label: "Pay", icon: CreditCard },
  { href: "/tenant/history", label: "History", icon: Receipt },
  { href: "/tenant/lease", label: "Lease", icon: FileText },
  { href: "/tenant/plan", label: "Plan", icon: CalendarRange },
  { href: "/tenant/notifications", label: "Inbox", icon: Bell },
  { href: "/tenant/profile", label: "Profile", icon: User },
];

export function TenantBottomNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary"
      className="sticky bottom-0 z-30 border-t bg-background md:hidden"
    >
      <ul className="grid grid-cols-7">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href ||
            (href !== "/tenant" && pathname?.startsWith(href));
          return (
            <li key={href}>
              <Link
                href={href}
                className={cn(
                  "flex flex-col items-center justify-center gap-0.5 py-2 text-[10px] transition-colors",
                  active ? "text-primary" : "text-muted-foreground"
                )}
              >
                <Icon className="h-5 w-5" aria-hidden />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function TenantSidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden md:flex h-screen w-56 flex-col border-r bg-card">
      <div className="flex h-14 items-center px-4 border-b">
        <span className="font-semibold tracking-tight text-primary">
          Landloads
        </span>
      </div>
      <nav className="flex-1 overflow-y-auto p-3" aria-label="Primary">
        <ul className="space-y-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active =
              pathname === href ||
              (href !== "/tenant" && pathname?.startsWith(href));
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
