import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ThreadsBot Factory — AI-powered Threads Automation",
  description: "Manage hundreds of Threads accounts. Auto-posting, proxies, templates, analytics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="antialiased">
        <div className="bg-orb bg-orb-1" />
        <div className="bg-orb bg-orb-2" />
        <div className="bg-orb bg-orb-3" />
        {children}
      </body>
    </html>
  );
}
