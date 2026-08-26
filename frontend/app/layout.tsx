import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'A股智能投研平台',
  description: 'A-share Intelligent Investment Research Platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
