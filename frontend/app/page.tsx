'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { marketApi, analysisApi } from '@/lib/api'
import type { MarketOverview, QuoteData, ScreeningCandidate, DataMeta } from '@/lib/types'
import { DataStateBanner, Skeleton } from '@/components/DataState'
import { MockBadge } from '@/components/MockBadge'
import {
  formatPrice, formatPct, formatAmount, formatVolume,
  changeColor, changeBg, scoreColor, recommendationLabel,
} from '@/lib/utils'

export default function MarketDashboard() {
  const [overview, setOverview] = useState<MarketOverview | null>(null)
  const [aiPicks, setAiPicks] = useState<ScreeningCandidate[]>([])
  const [hotQuotes, setHotQuotes] = useState<QuoteData[]>([])
  const [meta, setMeta] = useState<DataMeta>({ state: 'LOADING' })
  const [aiMeta, setAiMeta] = useState<DataMeta>({ state: 'LOADING' })

  const fetchOverview = useCallback(async () => {
    try {
      const data = await marketApi.getOverview()
      setOverview(data)
      setMeta({ state: 'SUCCESS', timestamp: data.timestamp, source: data.data_source })
    } catch (err) {
      setMeta({ state: 'ERROR', error: err instanceof Error ? err.message : 'Failed' })
    }
  }, [])

  const fetchAiPicks = useCallback(async () => {
    try {
      const result = await analysisApi.findCandidates('趋势最强', 5)
      setAiPicks(result.candidates)
      // Fetch quotes for AI picks
      if (result.candidates.length > 0) {
        const symbols = result.candidates.map(c => c.symbol)
        const quotes = await marketApi.getQuotes(symbols)
        setHotQuotes(quotes)
      }
      setAiMeta({ state: 'SUCCESS', source: 'api' })
    } catch {
      setAiMeta({ state: 'ERROR', error: 'AI analysis unavailable' })
    }
  }, [])

  useEffect(() => {
    fetchOverview()
    fetchAiPicks()
    const timer = setInterval(fetchOverview, 30000)
    return () => clearInterval(timer)
  }, [fetchOverview, fetchAiPicks])

  const indices = overview?.indices ? Object.entries(overview.indices) : []

  return (
    <div className="max-w-7xl mx-auto px-3 py-3 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-neutral-900">A股市场</h1>
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <span>{overview ? '交易中' : '—'}</span>
            <span>·</span>
            <span>{overview?.timestamp ? new Date(overview.timestamp).toLocaleString('zh-CN') : '—'}</span>
            <MockBadge source={overview?.data_source} />
          </div>
        </div>
        <button onClick={fetchOverview} className="btn-outline text-xs py-1.5 px-3">
          刷新
        </button>
      </div>

      <DataStateBanner meta={meta} />

      {/* Market Indices */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {indices.length > 0 ? indices.map(([name, idx]) => (
          <div key={name} className={`card p-3 ${changeBg(idx.change_pct)}`}>
            <div className="text-xs text-neutral-500 mb-1">{name}</div>
            <div className="text-lg font-bold font-mono tabular-nums">
              {formatPrice(idx.price)}
            </div>
            <div className={`text-sm font-mono font-medium ${changeColor(idx.change_pct)}`}>
              {formatPct(idx.change_pct)}
            </div>
          </div>
        )) : (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card p-3"><Skeleton className="h-16" /></div>
          ))
        )}
      </div>

      {/* Market Breadth */}
      {overview && (
        <div className="card">
          <div className="card-header">市场概览</div>
          <div className="card-body">
            <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
              <StatItem label="上涨" value={String(overview.up_count)} color="text-up" />
              <StatItem label="下跌" value={String(overview.down_count)} color="text-down" />
              <StatItem label="涨停" value={String(overview.limit_up_count)} color="text-up" />
              <StatItem label="跌停" value={String(overview.limit_down_count)} color="text-down" />
              <StatItem label="成交额" value={formatAmount(overview.total_amount)} />
              <StatItem label="北向资金" value={formatAmount(overview.northbound_flow)} color={changeColor(overview.northbound_flow)} />
            </div>
          </div>
        </div>
      )}

      {/* Hot Sectors (from stock list) */}
      <HotSectors />

      {/* AI Picks */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <span>AI精选 · 趋势最强</span>
          <Link href="/analysis" className="text-xs text-blue-600 hover:underline">
            查看更多 →
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-neutral-500 border-b border-neutral-100">
                <th className="text-left table-cell font-medium">股票</th>
                <th className="text-right table-cell font-medium">最新价</th>
                <th className="text-right table-cell font-medium">涨跌幅</th>
                <th className="text-right table-cell font-medium">AI评分</th>
                <th className="text-center table-cell font-medium">信号</th>
              </tr>
            </thead>
            <tbody>
              {aiPicks.length > 0 ? aiPicks.map((pick, i) => {
                const quote = hotQuotes.find(q => q.symbol === pick.symbol)
                return (
                  <tr key={pick.symbol} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                    <td className="table-cell">
                      <Link href={`/stock/${pick.symbol}`} className="hover:text-blue-600">
                        <div className="font-medium text-sm">{pick.name || pick.symbol}</div>
                        <div className="text-xs text-neutral-400">{pick.symbol}</div>
                      </Link>
                    </td>
                    <td className="table-cell text-right font-mono tabular-nums">
                      {quote ? formatPrice(quote.price) : <Skeleton className="h-4 w-14 ml-auto" />}
                    </td>
                    <td className={`table-cell text-right font-mono tabular-nums ${changeColor(quote?.change_pct)}`}>
                      {quote ? formatPct(quote.change_pct) : '—'}
                    </td>
                    <td className="table-cell text-right">
                      <span className={`font-bold font-mono ${scoreColor(pick.score)}`}>
                        {pick.score.toFixed(0)}
                      </span>
                    </td>
                    <td className="table-cell text-center">
                      <Link
                        href={`/analysis/${pick.symbol}`}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        AI分析
                      </Link>
                    </td>
                  </tr>
                )
              }) : (
                <tr>
                  <td colSpan={5} className="table-cell text-center text-neutral-400">
                    {aiMeta.state === 'LOADING' ? '加载中...' : aiMeta.state === 'ERROR' ? 'AI分析暂不可用' : '无数据'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Strategy Performance placeholder */}
      <div className="card">
        <div className="card-header">策略表现</div>
        <div className="card-body text-center py-8 text-neutral-400 text-sm">
          <Link href="/strategy" className="text-blue-600 hover:underline">
            前往策略中心查看 →
          </Link>
        </div>
      </div>
    </div>
  )
}

function StatItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="text-center">
      <div className="text-xs text-neutral-500 mb-0.5">{label}</div>
      <div className={`text-sm font-bold font-mono tabular-nums ${color || 'text-neutral-800'}`}>
        {value}
      </div>
    </div>
  )
}

/**
 * Hot sectors - derived from stock list grouped by industry.
 */
function HotSectors() {
  const [sectors, setSectors] = useState<{ name: string; count: number; symbols: string[] }[]>([])

  useEffect(() => {
    (async () => {
      try {
        const stocks = await marketApi.getStockList()
        const grouped: Record<string, string[]> = {}
        for (const s of stocks) {
          if (!grouped[s.industry]) grouped[s.industry] = []
          grouped[s.industry].push(s.symbol)
        }
        const result = Object.entries(grouped)
          .map(([name, symbols]) => ({ name, count: symbols.length, symbols }))
          .sort((a, b) => b.count - a.count)
        setSectors(result)
      } catch { /* ignore */ }
    })()
  }, [])

  if (sectors.length === 0) return null

  return (
    <div className="card">
      <div className="card-header">热门板块</div>
      <div className="card-body">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          {sectors.map(sector => (
            <Link
              key={sector.name}
              href={`/stock/${sector.symbols[0]}`}
              className="flex items-center justify-between p-2.5 rounded-md bg-neutral-50 hover:bg-neutral-100 transition-colors"
            >
              <span className="text-sm font-medium">{sector.name}</span>
              <span className="text-xs text-neutral-400">{sector.count}只</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
