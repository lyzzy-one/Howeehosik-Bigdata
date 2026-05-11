import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "안심귀가 - 우리 동네 안전도 분석",
  description: "AI 기반 귀가 안전도 분석 서비스",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-slate-50">{children}</body>
    </html>
  );
}
