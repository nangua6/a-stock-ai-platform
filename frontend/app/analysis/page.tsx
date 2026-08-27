'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { marketApi, analysisApi } from '@/lib/api'
import type { StockListItem, QuoteData, StockAnalysisResult, DataMeta } from '@/lib/types'
import { DataStateBanner } from '@/components/DataState'
import { MockBadge } from '@/components/MockBadge'
import {
  formatPrice, formatPct, changeColor, scoreColor,
  recommendationColor, recommendationLabel,
} from '@/lib/utils'

export default function AnalysisPage() {
  const [stocks, setStocks] = useState<StockListItem[]>([])
  const [results, setResults] = useState<Map<string, StockAnalysisResult>>(new Map())
  const [quotes, setQuotes] = useState<Map<string, QuoteData>>(new Map())
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [meta, setMeta] = useState<DataMeta>({ state: 'LOADING' })

  useEffect(() => {
    (async () => {
      try {
        const list = await marketApi.getStockList()
        setStocks(list)
        // Fetch all quotes
        const symbols = list.map(s => s.symbol)
        const q = await marketApi.getQuotes(symbols)
        const qMap = new Map<string, QuoteData>()
        q.forEach(quote => qMap.set(quote.symbol, quote))
        setQuotes(qMap)
        setMeta({ state: 'SUCCESS', source: q[0]?.data_source })
      } catch {
        setMeta({ state: 'ERROR', error: 'Failed to load stocks' })
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const analyzeAll = useCallback(async () => {
    setAnalyzing(true)
    const newResults = new Map<string, StockAnalysisResult>()
    for (const stock of stocks) {
      try {
        const result = await analysisApi.analyzeStock(stock.symbol)
        newResults.set(stock.symbol, result)
        setResults(new Map(newResults))
      } catch { /* skip failed */ }
    }
    setAnalyzing(false)
  }, [stocks])

  return (
    <div className="max-w-7xl mx-auto px-3 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold">AI投研中心</h1>
          <div className="text-xs text-neutral-500">
            全市场 AI 扫描 · {stocks.length} 只股票
          </div>
        </div>
        <button
          className="btn-primary text-xs py-1.5"
          onClick={analyzeAll}
          disabled={analyzing}
        >
          {analyzing ? '分析中...' : 'AI全量扫描'}
        </button>
      </div>

      <DataStateBanner meta={meta} />

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-neutral-500 border-b border-neutral-100">
                <th className="text-left table-cell font-medium">股票</th>
                <th className="text-right table-cell font-medium">最新价</th>
                <th className="text-right table-cell font-medium">涨跌幅</th>
                <th className="text-right table-cell font-medium">综合评分</th>
                <th className="text-right table-cell font-medium">技术评分</th>
                <th className="text-center table-cell font-medium">建议</th>
                <th className="text-center table-cell font-medium">风险</th>
                <th className="text-center table-cell font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="table-cell text-center text-neutral-400">加载中...</td>
                </tr>
              ) : stocks.map(stock => {
                const quote = quotes.get(stock.symbol)
                const result = results.get(stock.symbol)
                return (
                  <tr key={stock.symbol} className="border-b border-neutral-50 hover:bg-neutral-50">
                    <td className="table-cell">
                      <Link href={`/stock/${stock.symbol}`} className="hover:text-blue-600">
                        <div className="font-medium text-sm">{stock.name}</div>
                        <div className="text-xs text-neutral-400">{stock.symbol}</div>
                      </Link>
                    </td>
                    <td className="table-cell text-right font-mono tabular-nums">
                      {quote ? formatPrice(quote.price) : '—'}
                    </td>
                    <td className={`table-cell text-right font-mono tabular-nums ${changeColor(quote?.change_pct)}`}>
                      {quote ? formatPct(quote.change_pct) : '—'}
                    </td>
                    <td className="table-cell text-right">
                      {result ? (
                        <span className={`font-bold font-mono ${scoreColor(result.overall_score)}`}>
                          {result.overall_score.toFixed(0)}
                        </span>
                      ) : analyzing ? (
                        <span className="text-xs text-neutral-400">...</span>
                      ) : '—'}
                    </td>
                    <td className="table-cell text-right">
                      {result ? (
                        <span className={`font-mono ${scoreColor(result.technical.score)}`}>
                          {result.technical.score.toFixed(0)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="table-cell text-center">
                      {result ? (
                        <span className={`badge border ${recommendationColor(result.recommendation)}`}>
                          {recommendationLabel(result.recommendation)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="table-cell text-center">
                      {result ? (
                        <span className={`badge ${result.risk.risk_level === 'HIGH' ? 'bg-red-50 text-red-600' : result.risk.risk_level === 'LOW' ? 'bg-green-50 text-green-600' : 'bg-amber-50 text-amber-600'}`}>
                          {result.risk.risk_level}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="table-cell text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Link href={`/stock/${stock.symbol}`} className="text-xs text-blue-600 hover:underline">
                          行情
                        </Link>
                        <span className="text-neutral-300">|</span>
                        <Link href={`/analysis/${stock.symbol}`} className="text-xs text-blue-600 hover:underline">
                          详情
                        </Link>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
