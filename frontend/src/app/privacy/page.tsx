import Link from "next/link";

export const metadata = {
  title: "Privacy notice — Landloads",
  description: "How Landloads collects, uses, and protects your data.",
};

export default function PrivacyNoticePage() {
  return (
    <main className="container max-w-2xl py-12">
      <Link href="/" className="text-sm text-primary hover:underline">
        ← Back home
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">Privacy notice</h1>
      <p className="mt-2 text-sm text-muted-foreground">Last updated 2026-05-09.</p>

      <section className="mt-8 space-y-3 text-sm leading-6">
        <h2 className="text-lg font-semibold">What we collect</h2>
        <ul className="list-disc pl-5">
          <li>Name, phone, and email.</li>
          <li>
            Kenyan ID number and KRA PIN (encrypted at rest with{" "}
            <code>pgcrypto</code>; never logged).
          </li>
          <li>M-Pesa transaction receipts and amounts.</li>
          <li>Lease, invoice, payment, and audit history.</li>
        </ul>

        <h2 className="text-lg font-semibold">Why we collect it</h2>
        <ul className="list-disc pl-5">
          <li>To operate your tenancy with your landlord.</li>
          <li>To send rent reminders, OTPs, and payment receipts.</li>
          <li>
            To comply with KRA and the Kenyan Data Protection Act.
          </li>
        </ul>

        <h2 className="text-lg font-semibold">Retention</h2>
        <p>
          We keep your records for <strong>seven years</strong> after your last
          lease ends, as required by Kenyan tax and tenancy regulations. You
          can request a deletion review by emailing{" "}
          <a className="text-primary hover:underline" href="mailto:privacy@landloads.example.co.ke">
            privacy@landloads.example.co.ke
          </a>
          .
        </p>

        <h2 className="text-lg font-semibold">Your rights</h2>
        <ul className="list-disc pl-5">
          <li>
            <code>GET /api/me/export</code> — download your data as JSON.
          </li>
          <li>
            <code>POST /api/me/deletion-request</code> — schedule deletion
            after the seven-year clock expires.
          </li>
          <li>
            Email <a className="text-primary hover:underline" href="mailto:privacy@landloads.example.co.ke">
              privacy@landloads.example.co.ke
            </a>{" "}
            to dispute or correct any record.
          </li>
        </ul>
      </section>
    </main>
  );
}
