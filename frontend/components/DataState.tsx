'use client'

import type { DataMeta } from '@/lib/types'

/**
 * Shows data freshness state. Renders nothing when data is normal.
 * Shows loading spinner, error message, or stale/unavailable warnings.
 */
export function DataStateBanner({ meta }: { meta: DataMeta }) {
  if (meta.state === 'LOADING') {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 text-xs">
        <div className="w-3 h-3 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
        加载中...
      </div>
    )
  }

  if (meta.state === 'ERROR') {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 text-red-700 text-xs">
        <span className="font-bold">ERROR</span>
        <span>{meta.error || '请求失败'}</span>
      </div>
    )
  }

  if (meta.state === 'UNAVAILABLE') {
    return (
      <div className="flex items-center justify-center px-3 py-4 bg-neutral-100 text-neutral-500 text-sm">
        DATA_UNAVAILABLE
      </div>
    )
  }

  if (meta.state === 'STALE') {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 text-amber-700 text-xs">
        <span className="font-bold">STALE</span>
        <span>数据已过期 · {meta.dataAge || ''}</span>
      </div>
    )
  }

  return null
}

/**
 * Loading skeleton block.
 */
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-neutral-200 rounded ${className}`} />
}

/**
 * Full-page loading state.
 */
export function PageLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="w-8 h-8 border-3 border-neutral-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-3" style={{ borderWidth: '3px' }} />
        <div className="text-sm text-neutral-500">加载中...</div>
      </div>
    </div>
  )
}
