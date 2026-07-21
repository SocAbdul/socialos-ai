import type { Metadata } from "next";
import { Geist } from "next/font/google";

import { AuthProvider } from "@/components/auth-provider";

import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" });

export const metadata: Metadata = {
  title: "SocialOS AI",
  description: "The AI operating system for multi-platform marketing.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={geist.className}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

