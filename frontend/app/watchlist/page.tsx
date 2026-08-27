'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { watchlistApi } from '@/lib/api'
import type { WatchlistItem, DataMeta } from '@/lib/types'
import { DataStateBanner } from '@/components/DataState'
import { MockBadge } from '@/components/MockBadge'
import {
  formatPrice, formatPct, formatAmount, formatVolume,
  changeColor,
} from '@/lib/utils'

type SortKey = 'name' | 'change_pct' | 'price'

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [meta, setMeta] = useState<DataMeta>({ state: 'LOADING' })
  const [sortBy, setSortBy] = useState<SortKey>('name')
  const [removing, setRemoving] = useState<string | null>(null)

  const fetchWatchlist = useCallback(async () => {
    setMeta({ state: 'LOADING' })
    try {
      const data = await watchlistApi.getAll()
      setItems(data)
      setMeta({ state: 'SUCCESS', source: data[0]?.quote?.data_source })
    } catch (err) {
      setMeta({ state: 'ERROR', error: err instanceof Error ? err.message : 'Failed' })
    }
  }, [])

  useEffect(() => { fetchWatchlist() }, [fetchWatchlist])

  const handleRemove = async (symbol: string) => {
    setRemoving(symbol)
    try {
      await watchlistApi.remove(symbol)
      setItems(prev => prev.filter(i => i.symbol !== symbol))
    } catch {
      alert('删除失败')
    } finally {
      setRemoving(null)
    }
  }

  const sorted = [...items].sort((a, b) => {
    if (sortBy === 'name') return (a.name || '').localeCompare(b.name || '')
    if (sortBy === 'change_pct') return (b.quote?.change_pct ?? 0) - (a.quote?.change_pct ?? 0)
    if (sortBy === 'price') return (b.quote?.price ?? 0) - (a.quote?.price ?? 0)
    return 0
  })

  return (
    <div className="page-container">
      <div className="flex items-center justify-between">
        <div>
          <h1>自选股</h1>
          <p className="text-sm text-neutral-500 mt-1">
            关注你的核心股票与 AI 信号 · {items.length} 只
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="text-xs border border-neutral-300 rounded px-2 py-1.5 bg-white"
            value={sortBy}
            onChange={e => setSortBy(e.target.value as SortKey)}
          >
            <option value="name">按名称</option>
            <option value="change_pct">按涨跌幅</option>
            <option value="price">按价格</option>
          </select>
          <button onClick={fetchWatchlist} className="btn-outline text-xs py-1.5">
            刷新
          </button>
        </div>
      </div>

      <DataStateBanner meta={meta} />

      {meta.state === 'SUCCESS' && items.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">⭐</div>
            <div className="empty-state-title">还没有自选股票</div>
            <div className="empty-state-desc mb-6">
              从市场或 AI 投研中添加股票到自选，方便跟踪核心标的和 AI 信号。
            </div>
            <div className="flex items-center gap-3">
              <Link href="/" className="btn-primary">去市场</Link>
              <Link href="/analysis" className="btn-outline">去 AI 投研</Link>
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-neutral-500 border-b border-neutral-100">
                  <th className="text-left table-cell font-medium">股票</th>
                  <th className="text-right table-cell font-medium">最新价</th>
                  <th className="text-right table-cell font-medium">涨跌幅</th>
                  <th className="text-right table-cell font-medium">成交额</th>
                  <th className="text-right table-cell font-medium">成交量</th>
                  <th className="text-center table-cell font-medium">数据源</th>
                  <th className="text-center table-cell font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map(item => {
                  const q = item.quote
                  return (
                    <tr key={item.symbol} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                      <td className="table-cell">
                        <Link href={`/stock/${item.symbol}`} className="hover:text-blue-600">
                          <div className="font-medium text-sm">{item.name || item.symbol}</div>
                          <div className="text-xs text-neutral-400">{item.symbol}</div>
                        </Link>
                      </td>
                      <td className="table-cell text-right font-mono tabular-nums">
                        {q ? formatPrice(q.price) : '—'}
                      </td>
                      <td className={`table-cell text-right font-mono tabular-nums ${changeColor(q?.change_pct)}`}>
                        {q ? formatPct(q.change_pct) : '—'}
                      </td>
                      <td className="table-cell text-right font-mono tabular-nums text-xs">
                        {q ? formatAmount(q.amount) : '—'}
                      </td>
                      <td className="table-cell text-right font-mono tabular-nums text-xs">
                        {q ? formatVolume(q.volume) : '—'}
                      </td>
                      <td className="table-cell text-center">
                        <MockBadge source={q?.data_source} />
                        {!q && <span className="text-xs text-neutral-400">NO DATA</span>}
                      </td>
                      <td className="table-cell text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Link href={`/analysis/${item.symbol}`} className="text-xs text-blue-600 hover:underline">
                            AI分析
                          </Link>
                          <button
                            className="text-xs text-red-500 hover:text-red-700 disabled:opacity-50"
                            onClick={() => handleRemove(item.symbol)}
                            disabled={removing === item.symbol}
                          >
                            {removing === item.symbol ? '...' : '移除'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
