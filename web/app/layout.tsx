import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Providers } from "./providers";

// Fonts load at runtime, not at build time, so `next build` (and the Docker image) works offline.
// If the stylesheet cannot load, the system-ui fallbacks in globals.css are used.
const FONT_CSS =
  "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;500&display=swap";

export const metadata: Metadata = {
  title: "RORA · Ops console",
  description: "Ask questions of your data in plain language and review the SQL before it runs.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="stylesheet" href={FONT_CSS} />
      </head>
      <body className="min-h-screen antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
