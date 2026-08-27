'use client'

import { useEffect, useState, useCallback, use } from 'react'
import Link from 'next/link'
import { marketApi, analysisApi, watchlistApi } from '@/lib/api'
import type {
  QuoteData, KlineBar, TechnicalIndicators, FinancialData,
  StockAnalysisResult, DataMeta,
} from '@/lib/types'
import { DataStateBanner, Skeleton } from '@/components/DataState'
import { MockBadge } from '@/components/MockBadge'
import { KlineChart } from '@/components/KlineChart'
import {
  formatPrice, formatPct, formatAmount, formatVolume,
  changeColor, changeBg, scoreColor, riskLevelColor,
  recommendationColor, recommendationLabel, trendLabel,
} from '@/lib/utils'

type TabId = 'quote' | 'technical' | 'fundamental' | 'ai' | 'risk'

export default function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = use(params)
  const [tab, setTab] = useState<TabId>('quote')

  const [quote, setQuote] = useState<QuoteData | null>(null)
  const [klines, setKlines] = useState<KlineBar[]>([])
  const [technicals, setTechnicals] = useState<TechnicalIndicators | null>(null)
  const [financials, setFinancials] = useState<FinancialData | null>(null)
  const [analysis, setAnalysis] = useState<StockAnalysisResult | null>(null)
  const [meta, setMeta] = useState<DataMeta>({ state: 'LOADING' })
  const [klineTf, setKlineTf] = useState('D')
  const [isInWatchlist, setIsInWatchlist] = useState(false)
  const [watchlistLoading, setWatchlistLoading] = useState(false)

  const fetchQuote = useCallback(async () => {
    try {
      const q = await marketApi.getQuote(symbol)
      setQuote(q)
      setMeta({ state: 'SUCCESS', timestamp: q.timestamp, source: q.data_source })
    } catch {
      setMeta({ state: 'ERROR', error: 'Failed to load quote' })
    }
  }, [symbol])

  const fetchKlines = useCallback(async (tf: string) => {
    try {
      const data = await marketApi.getKline(symbol, tf, 120)
      setKlines(data)
    } catch { /* ignore */ }
  }, [symbol])

  const fetchTechnicals = useCallback(async () => {
    try {
      const data = await marketApi.getTechnical(symbol)
      setTechnicals(data)
    } catch { /* ignore */ }
  }, [symbol])

  const fetchFinancials = useCallback(async () => {
    try {
      const data = await marketApi.getFinancial(symbol)
      setFinancials(data)
    } catch { /* ignore */ }
  }, [symbol])

  const fetchAnalysis = useCallback(async () => {
    try {
      const data = await analysisApi.analyzeStock(symbol)
      setAnalysis(data)
    } catch { /* ignore */ }
  }, [symbol])

  useEffect(() => {
    fetchQuote()
    fetchKlines(klineTf)
    fetchTechnicals()
    fetchFinancials()
    const timer = setInterval(fetchQuote, 15000)
    return () => clearInterval(timer)
  }, [fetchQuote, fetchKlines, fetchTechnicals, fetchFinancials, klineTf])

  // Lazy load analysis when AI tab is selected
  useEffect(() => {
    if (tab === 'ai' && !analysis) fetchAnalysis()
  }, [tab, analysis, fetchAnalysis])

  // Check watchlist status
  useEffect(() => {
    watchlistApi.check(symbol).then(r => setIsInWatchlist(r.in_watchlist)).catch(() => {})
  }, [symbol])

  const toggleWatchlist = async () => {
    setWatchlistLoading(true)
    try {
      if (isInWatchlist) {
        await watchlistApi.remove(symbol)
        setIsInWatchlist(false)
      } else {
        await watchlistApi.add(symbol, quote?.name || '')
        setIsInWatchlist(true)
      }
    } catch {
      alert('操作失败，请重试')
    } finally {
      setWatchlistLoading(false)
    }
  }

  const handleTimeframeChange = (tf: string) => {
    setKlineTf(tf)
    fetchKlines(tf)
  }

  return (
    <div className="max-w-7xl mx-auto px-3 py-3 space-y-3">
      <DataStateBanner meta={meta} />

      {/* Stock Header */}
      <StockHeader quote={quote} symbol={symbol} />

      {/* Action Bar */}
      <div className="flex items-center gap-2">
        <Link href={`/analysis/${symbol}`} className="btn-primary text-xs py-1.5">
          AI分析
        </Link>
        <button className={`text-xs py-1.5 px-4 rounded-md font-medium transition-colors ${isInWatchlist ? 'bg-amber-50 text-amber-700 border border-amber-300 hover:bg-amber-100' : 'btn-outline'}`} onClick={toggleWatchlist} disabled={watchlistLoading}>
          {isInWatchlist ? '★ 已自选' : '☆ 加自选'}
        </button>
        <button className="btn-outline text-xs py-1.5" onClick={() => alert('模拟交易开发中')}>
          模拟交易
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-neutral-200 flex gap-0 overflow-x-auto">
        {([
          ['quote', '行情'],
          ['technical', '技术'],
          ['fundamental', '基本面'],
          ['ai', 'AI分析'],
          ['risk', '风险'],
        ] as [TabId, string][]).map(([id, label]) => (
          <button
            key={id}
            className={`tab whitespace-nowrap ${tab === id ? 'tab-active' : ''}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'quote' && (
        <QuoteTab
          klines={klines}
          klineTf={klineTf}
          onTimeframeChange={handleTimeframeChange}
          quote={quote}
        />
      )}
      {tab === 'technical' && <TechnicalTab technicals={technicals} />}
      {tab === 'fundamental' && <FundamentalTab financials={financials} />}
      {tab === 'ai' && <AiTab analysis={analysis} />}
      {tab === 'risk' && <RiskTab analysis={analysis} />}
    </div>
  )
}

// ── Stock Header ───────────────────────────────────────────────────────────

function StockHeader({ quote, symbol }: { quote: QuoteData | null; symbol: string }) {
  if (!quote) {
    return (
      <div className="card p-4">
        <Skeleton className="h-12 w-full" />
      </div>
    )
  }

  return (
    <div className="flex items-start justify-between flex-wrap gap-2">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold">{quote.name}</h1>
          <span className="text-sm text-neutral-400">{symbol}</span>
          <MockBadge source={quote.data_source} />
        </div>
        <div className="flex items-baseline gap-3 mt-1">
          <span className={`text-2xl font-bold font-mono tabular-nums ${changeColor(quote.change_pct)}`}>
            {formatPrice(quote.price)}
          </span>
          <span className={`text-base font-mono font-medium ${changeColor(quote.change_pct)}`}>
            {formatPct(quote.change_pct)}
          </span>
          <span className="text-sm text-neutral-500 font-mono">
            {quote.change > 0 ? '+' : ''}{quote.change.toFixed(2)}
          </span>
        </div>
      </div>
      <div className="text-right text-xs text-neutral-500 space-y-0.5">
        <div>成交量: <span className="font-mono">{formatVolume(quote.volume)}</span></div>
        <div>成交额: <span className="font-mono">{formatAmount(quote.amount)}</span></div>
        <div>更新: {new Date(quote.timestamp).toLocaleTimeString('zh-CN')}</div>
      </div>
    </div>
  )
}

// ── Quote Tab (K-line) ─────────────────────────────────────────────────────

function QuoteTab({
  klines, klineTf, onTimeframeChange, quote,
}: {
  klines: KlineBar[]
  klineTf: string
  onTimeframeChange: (tf: string) => void
  quote: QuoteData | null
}) {
  return (
    <div className="space-y-3">
      {/* Timeframe selector */}
      <div className="flex gap-1">
        {[
          ['D', '日K'],
          ['W', '周K'],
          ['M', '月K'],
        ].map(([tf, label]) => (
          <button
            key={tf}
            className={`px-3 py-1 text-xs rounded ${klineTf === tf ? 'bg-blue-600 text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}`}
            onClick={() => onTimeframeChange(tf)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* K-line chart */}
      <div className="card">
        <div className="card-body p-2">
          {klines.length > 0 ? (
            <KlineChart data={klines} />
          ) : (
            <div className="h-64 flex items-center justify-center text-neutral-400 text-sm">
              DATA_UNAVAILABLE
            </div>
          )}
        </div>
      </div>

      {/* Quick quote info */}
      {quote && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          <QuoteField label="开盘" value={formatPrice(quote.open)} />
          <QuoteField label="最高" value={formatPrice(quote.high)} />
          <QuoteField label="最低" value={formatPrice(quote.low)} />
          <QuoteField label="昨收" value={formatPrice(quote.pre_close)} />
          <QuoteField label="买一" value={`${formatPrice(quote.bid1_price)} × ${quote.bid1_volume}`} />
          <QuoteField label="卖一" value={`${formatPrice(quote.ask1_price)} × ${quote.ask1_volume}`} />
        </div>
      )}
    </div>
  )
}

function QuoteField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between p-2 bg-neutral-50 rounded text-sm">
      <span className="text-neutral-500">{label}</span>
      <span className="font-mono tabular-nums">{value}</span>
    </div>
  )
}

// ── Technical Tab ──────────────────────────────────────────────────────────

function TechnicalTab({ technicals }: { technicals: TechnicalIndicators | null }) {
  if (!technicals) {
    return <div className="text-center py-8 text-neutral-400 text-sm">加载中...</div>
  }

  return (
    <div className="space-y-3">
      {/* Moving Averages */}
      <div className="card">
        <div className="card-header">均线</div>
        <div className="card-body">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            <IndicatorField label="MA5" value={formatPrice(technicals.ma5)} />
            <IndicatorField label="MA10" value={formatPrice(technicals.ma10)} />
            <IndicatorField label="MA20" value={formatPrice(technicals.ma20)} />
            <IndicatorField label="MA60" value={formatPrice(technicals.ma60)} />
            <IndicatorField label="EMA12" value={formatPrice(technicals.ema12)} />
            <IndicatorField label="EMA26" value={formatPrice(technicals.ema26)} />
          </div>
        </div>
      </div>

      {/* Oscillators */}
      <div className="card">
        <div className="card-header">振荡指标</div>
        <div className="card-body">
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
            <IndicatorField label="MACD" value={technicals.macd_line.toFixed(4)} color={changeColor(technicals.macd_histogram)} />
            <IndicatorField label="Signal" value={technicals.macd_signal.toFixed(4)} />
            <IndicatorField label="Histogram" value={technicals.macd_histogram.toFixed(4)} color={changeColor(technicals.macd_histogram)} />
            <IndicatorField label="RSI(14)" value={technicals.rsi.toFixed(2)} color={technicals.rsi > 70 ? 'text-up' : technicals.rsi < 30 ? 'text-down' : ''} />
            <IndicatorField label="KDJ-K" value={technicals.kdj_k.toFixed(2)} />
            <IndicatorField label="KDJ-D" value={technicals.kdj_d.toFixed(2)} />
            <IndicatorField label="KDJ-J" value={technicals.kdj_j.toFixed(2)} />
          </div>
        </div>
      </div>

      {/* Bollinger & ATR */}
      <div className="card">
        <div className="card-header">波动指标</div>
        <div className="card-body">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            <IndicatorField label="BOLL上轨" value={formatPrice(technicals.boll_upper)} />
            <IndicatorField label="BOLL中轨" value={formatPrice(technicals.boll_middle)} />
            <IndicatorField label="BOLL下轨" value={formatPrice(technicals.boll_lower)} />
            <IndicatorField label="ATR(14)" value={technicals.atr.toFixed(4)} />
            <IndicatorField label="年化波动率" value={`${(technicals.volatility * 100).toFixed(2)}%`} />
            <IndicatorField label="振幅" value={`${technicals.amplitude}%`} />
          </div>
        </div>
      </div>

      {/* Volume */}
      <div className="card">
        <div className="card-header">成交量均线</div>
        <div className="card-body">
          <div className="grid grid-cols-3 gap-2">
            <IndicatorField label="VOL MA5" value={formatVolume(technicals.volume_ma5)} />
            <IndicatorField label="VOL MA10" value={formatVolume(technicals.volume_ma10)} />
            <IndicatorField label="VOL MA20" value={formatVolume(technicals.volume_ma20)} />
          </div>
        </div>
      </div>
    </div>
  )
}

function IndicatorField({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between p-2 bg-neutral-50 rounded text-sm">
      <span className="text-neutral-500 text-xs">{label}</span>
      <span className={`font-mono tabular-nums font-medium ${color || ''}`}>{value}</span>
    </div>
  )
}

// ── Fundamental Tab ────────────────────────────────────────────────────────

function FundamentalTab({ financials }: { financials: FinancialData | null }) {
  if (!financials) {
    return <div className="text-center py-8 text-neutral-400 text-sm">加载中...</div>
  }

  return (
    <div className="space-y-3">
      <div className="card">
        <div className="card-header">财务数据 <MockBadge source={financials.data_source} /></div>
        <div className="card-body">
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
            <IndicatorField label="PE(市盈率)" value={financials.pe_ratio.toFixed(2)} />
            <IndicatorField label="PB(市净率)" value={financials.pb_ratio.toFixed(2)} />
            <IndicatorField label="ROE(%)" value={`${financials.roe.toFixed(2)}%`} />
            <IndicatorField label="EPS" value={financials.eps.toFixed(2)} />
            <IndicatorField label="营收" value={formatAmount(financials.revenue)} />
            <IndicatorField label="净利润" value={formatAmount(financials.net_profit)} />
            <IndicatorField label="总市值" value={formatAmount(financials.market_cap)} />
            <IndicatorField label="报告期" value={financials.report_date} />
          </div>
        </div>
      </div>
    </div>
  )
}

// ── AI Analysis Tab ────────────────────────────────────────────────────────

function AiTab({ analysis }: { analysis: StockAnalysisResult | null }) {
  if (!analysis) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-neutral-200 border-t-blue-600 rounded-full animate-spin mr-3" />
        <span className="text-sm text-neutral-500">AI 分析中...</span>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <span>AI 综合分析</span>
          <MockBadge source={analysis.data_source} />
        </div>
        <div className="card-body space-y-4">
          {/* Score + Recommendation */}
          <div className="flex items-center gap-6 flex-wrap">
            <div className="text-center">
              <div className="text-xs text-neutral-500 mb-1">综合评分</div>
              <div className={`text-3xl font-bold font-mono ${scoreColor(analysis.overall_score)}`}>
                {analysis.overall_score.toFixed(0)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-neutral-500 mb-1">技术评分</div>
              <div className={`text-2xl font-bold font-mono ${scoreColor(analysis.technical.score)}`}>
                {analysis.technical.score.toFixed(0)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-neutral-500 mb-1">建议</div>
              <div className={`badge border text-sm px-3 py-1 ${recommendationColor(analysis.recommendation)}`}>
                {recommendationLabel(analysis.recommendation)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-neutral-500 mb-1">置信度</div>
              <div className="text-lg font-bold font-mono">
                {(analysis.confidence * 100).toFixed(0)}%
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-neutral-500 mb-1">趋势</div>
              <div className="text-sm font-medium">
                {trendLabel(analysis.technical.trend)}
              </div>
            </div>
          </div>

          {/* Data Quality */}
          <div className="text-xs text-neutral-400">
            数据质量: {analysis.data_quality} · 更新: {analysis.data_timestamp ? new Date(analysis.data_timestamp).toLocaleString('zh-CN') : '—'}
          </div>
        </div>
      </div>

      {/* Bull / Bear / Risks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="card">
          <div className="card-header text-up">Bull Case</div>
          <div className="card-body text-sm text-neutral-700">
            {analysis.bull_case || '暂无看多信号'}
          </div>
        </div>
        <div className="card">
          <div className="card-header text-down">Bear Case</div>
          <div className="card-body text-sm text-neutral-700">
            {analysis.bear_case || '暂无看空信号'}
          </div>
        </div>
        <div className="card">
          <div className="card-header text-amber-600">Key Risks</div>
          <div className="card-body text-sm text-neutral-700">
            {analysis.key_risks.length > 0 ? (
              <ul className="list-disc list-inside space-y-1">
                {analysis.key_risks.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            ) : '暂无关键风险'}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Risk Tab ───────────────────────────────────────────────────────────────

function RiskTab({ analysis }: { analysis: StockAnalysisResult | null }) {
  if (!analysis) {
    return (
      <div className="text-center py-8 text-neutral-400 text-sm">
        请先查看AI分析标签页
      </div>
    )
  }

  const risk = analysis.risk

  return (
    <div className="space-y-3">
      <div className="card">
        <div className="card-header">风险评估</div>
        <div className="card-body space-y-3">
          <div className="flex items-center gap-4">
            <div>
              <div className="text-xs text-neutral-500 mb-1">风险等级</div>
              <span className={`badge ${riskLevelColor(risk.risk_level)} text-sm px-3 py-1`}>
                {risk.risk_level}
              </span>
            </div>
            <div>
              <div className="text-xs text-neutral-500 mb-1">波动率</div>
              <span className="font-mono text-sm">{(risk.volatility * 100).toFixed(2)}%</span>
            </div>
            <div>
              <div className="text-xs text-neutral-500 mb-1">数据新鲜度</div>
              <span className={`text-sm ${risk.is_data_fresh ? 'text-green-600' : 'text-red-600'}`}>
                {risk.is_data_fresh ? 'FRESH' : `STALE (${risk.data_age_seconds.toFixed(0)}s)`}
              </span>
            </div>
          </div>

          {risk.key_risks.length > 0 && (
            <div>
              <div className="text-xs text-neutral-500 mb-2">风险项</div>
              <div className="space-y-1.5">
                {risk.key_risks.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 bg-amber-50 rounded text-sm">
                    <span className="text-amber-600 font-bold">⚠</span>
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
