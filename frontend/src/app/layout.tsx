import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Landloads",
  description: "Landlord management platform",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
