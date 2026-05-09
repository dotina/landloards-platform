import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="container flex h-14 items-center justify-between">
          <span className="text-lg font-semibold tracking-tight text-primary">
            Landloads
          </span>
          <nav className="flex items-center gap-2">
            <Link href="/auth/login">
              <Button variant="ghost">Sign in</Button>
            </Link>
            <Link href="/auth/landlord/register">
              <Button>Create landlord account</Button>
            </Link>
          </nav>
        </div>
      </header>
      <section className="container flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-6 py-12 text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          Rent management built for Kenyan landlords.
        </h1>
        <p className="max-w-xl text-lg text-muted-foreground">
          Collect rent via M-Pesa, track tenants, send reminders &mdash; with a
          calm, straightforward dashboard.
        </p>
        <div className="flex gap-3">
          <Link href="/auth/landlord/register">
            <Button size="lg">Get started</Button>
          </Link>
          <Link href="/auth/login">
            <Button size="lg" variant="outline">
              Sign in
            </Button>
          </Link>
        </div>
      </section>
    </main>
  );
}
