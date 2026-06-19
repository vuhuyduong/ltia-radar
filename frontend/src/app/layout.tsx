import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ClientLayout } from "@/components/layout/client-layout";

const inter = Inter({
  subsets: ["latin", "vietnamese"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "LTIA Radar — Hệ thống Cảnh báo sớm Sân bay Long Thành",
  description:
    "Hệ thống Radar Cảnh báo sớm & Quản trị khủng hoảng truyền thông cho Dự án Cảng Hàng không Quốc tế Long Thành",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                var theme = localStorage.getItem('theme') || 'light';
                document.documentElement.className = theme;
              })()
            `,
          }}
        />
      </head>
      <body className={`${inter.variable} font-sans antialiased bg-[hsl(var(--background))] text-[hsl(var(--foreground))] transition-colors duration-200`}>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
