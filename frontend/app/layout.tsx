import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RankReady — AI-Powered SEO & AEO Optimizer",
  description: "Score, optimize, and get cited by AI engines. The only SEO tool that audits ChatGPT citations and helps you rank in the era of answer engines.",
  openGraph: {
    title: "RankReady — AI-Powered SEO & AEO Optimizer",
    description: "Score, optimize, and get cited by AI engines.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
