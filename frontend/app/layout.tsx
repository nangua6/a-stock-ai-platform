import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Navigation } from '@/components/Navigation'

export const metadata: Metadata = {
  title: 'A股智能投研',
  description: 'A-share Intelligent Investment Research Terminal',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">
        <div className="flex flex-col lg:flex-row min-h-screen">
          {/* Desktop sidebar */}
          <aside className="hidden lg:block w-56 flex-shrink-0">
            <Navigation variant="sidebar" />
          </aside>
          {/* Main content */}
          <main className="flex-1 min-w-0 pb-16 lg:pb-0">
            {children}
          </main>
          {/* Mobile bottom nav */}
          <nav className="lg:hidden fixed bottom-0 inset-x-0 z-50">
            <Navigation variant="bottom" />
          </nav>
        </div>
      </body>
    </html>
  )
}
