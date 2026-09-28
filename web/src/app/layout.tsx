import type { Metadata } from "next";
import Link from "next/link";
import { Public_Sans } from "next/font/google";
import "./globals.css";

const publicSans = Public_Sans({ variable: "--font-public-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "ARGUS", template: "%s | ARGUS" },
  description:
    "Explainable multi-agent KYC risk screening: five agents investigate an entity and a human reviewer decides.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${publicSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-10 focus:rounded-md focus:bg-card focus:px-3 focus:py-2 focus:ring-3 focus:ring-ring"
        >
          Skip to content
        </a>
        <header className="border-b bg-card">
          <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 sm:px-6">
            <Link
              href="/"
              className="flex items-center gap-2 rounded-md font-semibold tracking-wide focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- a static SVG needs no optimisation */}
              <img src="/icon.svg" alt="" width={28} height={28} />
              <span className="text-lg">ARGUS</span>
            </Link>
            <span className="hidden text-sm text-muted-foreground sm:inline">
              KYC risk screening with cited evidence
            </span>
            <nav aria-label="Main" className="ml-auto">
              <Link
                href="/"
                className="rounded-md px-2 py-1 text-sm font-medium underline-offset-4 hover:underline focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
              >
                New assessment
              </Link>
            </nav>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
          {children}
        </main>
        <footer className="border-t">
          <p className="mx-auto max-w-6xl px-4 py-4 text-sm text-muted-foreground sm:px-6">
            Synthetic data and published enforcement facts only. ARGUS recommends; a human reviewer
            decides.
          </p>
        </footer>
      </body>
    </html>
  );
}
