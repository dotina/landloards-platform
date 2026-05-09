import type { ReactNode } from "react";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="container flex h-14 items-center">
          <span className="text-lg font-semibold tracking-tight text-primary">
            Landloads
          </span>
        </div>
      </header>
      <main className="container flex min-h-[calc(100vh-3.5rem)] items-center justify-center py-12">
        {children}
      </main>
    </div>
  );
}
