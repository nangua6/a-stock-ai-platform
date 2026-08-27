'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface NavItem {
  href: string
  label: string
  icon: string
  shortLabel?: string
}

const NAV_ITEMS: NavItem[] = [
  { href: '/', label: '市场', icon: 'M3 3h18v18H3V3zm2 2v14h14V5H5zm2 2h4v4H7V7zm6 0h4v2h-4V7zm0 4h4v2h-4v-2zM7 13h4v4H7v-4zm6 2h4v2h-4v-2z', shortLabel: '市场' },
  { href: '/watchlist', label: '自选', icon: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z', shortLabel: '自选' },
  { href: '/analysis', label: 'AI投研', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z', shortLabel: 'AI' },
  { href: '/strategy', label: '策略', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', shortLabel: '策略' },
  { href: '/system', label: '系统', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z', shortLabel: '系统' },
]

function SvgIcon({ path, className }: { path: string; className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" width="20" height="20">
      <path strokeLinecap="round" strokeLinejoin="round" d={path} />
    </svg>
  )
}

export function Navigation({ variant }: { variant: 'sidebar' | 'bottom' }) {
  const pathname = usePathname()

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname?.startsWith(href) ?? false
  }

  if (variant === 'sidebar') {
    return (
      <div className="fixed top-0 left-0 w-56 h-screen bg-neutral-950 text-white flex flex-col">
        {/* Logo */}
        <div className="px-5 py-4 border-b border-neutral-800">
          <div className="text-base font-bold tracking-tight">A股智能投研</div>
          <div className="text-[11px] text-neutral-500 mt-0.5">Quant Research Terminal</div>
        </div>

        {/* Nav items */}
        <nav className="flex-1 py-2 px-2 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(item => {
            const active = isActive(item.href)
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                  active
                    ? 'bg-neutral-800 text-white'
                    : 'text-neutral-400 hover:text-white hover:bg-neutral-800/50'
                }`}
              >
                <SvgIcon path={item.icon} className={active ? 'text-blue-400' : ''} />
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-neutral-800 text-[10px] text-neutral-600">
          v0.1.0 · MOCK DATA
        </div>
      </div>
    )
  }

  // Mobile bottom nav
  return (
    <div className="bg-white border-t border-neutral-200 flex items-stretch safe-area-bottom">
      {NAV_ITEMS.map(item => {
        const active = isActive(item.href)
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex-1 flex flex-col items-center justify-center py-2 text-[10px] transition-colors ${
              active ? 'text-blue-600' : 'text-neutral-400'
            }`}
          >
            <SvgIcon path={item.icon} className={active ? 'text-blue-600' : 'text-neutral-400'} />
            <span className="mt-0.5">{item.shortLabel || item.label}</span>
          </Link>
        )
      })}
    </div>
  )
}
