'use client'

import { useEffect, useState, useCallback, use } from 'react'
import Link from 'next/link'
import { marketApi, analysisApi } from '@/lib/api'
import type { StockAnalysisResult, QuoteData, DataMeta } from '@/lib/types'
import { DataStateBanner } from '@/components/DataState'
import { MockBadge } from '@/components/MockBadge'
import {
  formatPrice, formatPct, formatAmount, formatVolume,
  changeColor, scoreColor, riskLevelColor,
  recommendationColor, recommendationLabel, trendLabel,
} from '@/lib/utils'

export default function AnalysisDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = use(params)
  const [analysis, setAnalysis] = useState<StockAnalysisResult | null>(null)
  const [quote, setQuote] = useState<QuoteData | null>(null)
  const [meta, setMeta] = useState<DataMeta>({ state: 'LOADING' })

  const fetchData = useCallback(async () => {
    setMeta({ state: 'LOADING' })
    try {
      const [a, q] = await Promise.all([
        analysisApi.analyzeStock(symbol),
        marketApi.getQuote(symbol),
      ])
      setAnalysis(a)
      setQuote(q)
      setMeta({ state: 'SUCCESS', source: a.data_source })
    } catch (err) {
      setMeta({ state: 'ERROR', error: err instanceof Error ? err.message : 'Failed' })
    }
  }, [symbol])

  useEffect(() => { fetchData() }, [fetchData])

  return (
    <div className="max-w-5xl mx-auto px-3 py-3 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/stock/${symbol}`} className="text-neutral-400 hover:text-neutral-600 text-sm">
            ← 返回行情
          </Link>
          <h1 className="text-lg font-bold">
            {analysis?.name || symbol} <span className="text-neutral-400 font-normal text-sm">{symbol}</span>
          </h1>
          <MockBadge source={analysis?.data_source} />
        </div>
        <button onClick={fetchData} className="btn-outline text-xs py-1.5">
          重新分析
        </button>
      </div>

      <DataStateBanner meta={meta} />

      {analysis ? (
        <>
          {/* Score Overview */}
          <div className="card">
            <div className="card-header">综合评估</div>
            <div className="card-body">
              <div className="flex items-center gap-6 flex-wrap">
                {/* Overall Score */}
                <div className="text-center">
                  <div className="w-20 h-20 rounded-full border-4 border-neutral-100 flex items-center justify-center mx-auto mb-1"
                    style={{ borderColor: analysis.overall_score >= 70 ? '#ef4444' : analysis.overall_score >= 50 ? '#f59e0b' : '#22c55e' }}>
                    <span className={`text-2xl font-bold ${scoreColor(analysis.overall_score)}`}>
                      {analysis.overall_score.toFixed(0)}
                    </span>
                  </div>
                  <div className="text-xs text-neutral-500">综合评分</div>
                </div>

                {/* Technical Score */}
                <div className="text-center">
                  <div className="w-16 h-16 rounded-full border-3 border-neutral-100 flex items-center justify-center mx-auto mb-1"
                    style={{ borderWidth: '3px', borderColor: '#3b82f6' }}>
                    <span className={`text-lg font-bold ${scoreColor(analysis.technical.score)}`}>
                      {analysis.technical.score.toFixed(0)}
                    </span>
                  </div>
                  <div className="text-xs text-neutral-500">技术评分</div>
                </div>

                {/* Recommendation */}
                <div className="text-center">
                  <div className={`badge border text-lg px-4 py-2 ${recommendationColor(analysis.recommendation)}`}>
                    {recommendationLabel(analysis.recommendation)}
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">
                    置信度 {(analysis.confidence * 100).toFixed(0)}%
                  </div>
                </div>

                {/* Quick Stats */}
                <div className="flex-1 grid grid-cols-2 gap-2 ml-4">
                  <div className="text-sm">
                    <span className="text-neutral-500">趋势: </span>
                    <span className="font-medium">{trendLabel(analysis.technical.trend)}</span>
                  </div>
                  <div className="text-sm">
                    <span className="text-neutral-500">风险: </span>
                    <span className={`badge ${riskLevelColor(analysis.risk.risk_level)}`}>
                      {analysis.risk.risk_level}
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-neutral-500">价格: </span>
                    <span className={`font-mono ${changeColor(analysis.change_pct)}`}>
                      {formatPrice(analysis.current_price)} ({formatPct(analysis.change_pct)})
                    </span>
                  </div>
                  <div className="text-sm">
                    <span className="text-neutral-500">数据质量: </span>
                    <span>{analysis.data_quality}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Technical Details */}
          <div className="card">
            <div className="card-header">技术指标详情</div>
            <div className="card-body">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <MetricCard label="动量" value={analysis.technical.momentum.toFixed(3)} desc="-1 ~ +1" />
                <MetricCard label="成交量信号" value={analysis.technical.volume_signal.toFixed(3)} desc="-1 ~ +1" />
                <MetricCard label="均线排列" value={analysis.technical.ma_alignment.toFixed(3)} desc="-1 ~ +1" />
                <MetricCard label="RSI信号" value={analysis.technical.rsi_signal.toFixed(3)} desc="超卖 ~ 超买" />
                <MetricCard label="MACD信号" value={analysis.technical.macd_signal.toFixed(3)} desc="-1 ~ +1" />
                <MetricCard label="波动率" value={`${(analysis.risk.volatility * 100).toFixed(2)}%`} desc="越高风险越大" />
              </div>
            </div>
          </div>

          {/* Bull / Bear / Risks */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
            <div className="card">
              <div className="card-header flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-up" />
                <span>Bull Case</span>
              </div>
              <div className="card-body text-sm text-neutral-700 leading-relaxed">
                {analysis.bull_case || '暂无看多信号'}
              </div>
            </div>

            <div className="card">
              <div className="card-header flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-down" />
                <span>Bear Case</span>
              </div>
              <div className="card-body text-sm text-neutral-700 leading-relaxed">
                {analysis.bear_case || '暂无看空信号'}
              </div>
            </div>

            <div className="card">
              <div className="card-header flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>Key Risks</span>
              </div>
              <div className="card-body">
                {analysis.key_risks.length > 0 ? (
                  <ul className="space-y-2">
                    {analysis.key_risks.map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-amber-500 mt-0.5">⚠</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-sm text-neutral-400">暂无关键风险</div>
                )}
              </div>
            </div>
          </div>

          {/* Analysis Meta */}
          <div className="text-xs text-neutral-400 flex items-center gap-4">
            <span>分析时间: {new Date(analysis.analysis_timestamp).toLocaleString('zh-CN')}</span>
            <span>数据时间: {analysis.data_timestamp ? new Date(analysis.data_timestamp).toLocaleString('zh-CN') : '—'}</span>
            <span>数据源: {analysis.data_source}</span>
          </div>
        </>
      ) : meta.state === 'LOADING' ? (
        <div className="flex items-center justify-center py-16">
          <div className="w-8 h-8 border-3 border-neutral-200 border-t-blue-600 rounded-full animate-spin mr-3" style={{ borderWidth: '3px' }} />
          <span className="text-neutral-500">AI 分析引擎运行中...</span>
        </div>
      ) : (
        <div className="text-center py-16 text-neutral-400">
          分析失败，请重试
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, desc }: { label: string; value: string; desc?: string }) {
  return (
    <div className="p-3 bg-neutral-50 rounded-lg">
      <div className="text-xs text-neutral-500 mb-1">{label}</div>
      <div className="text-base font-bold font-mono tabular-nums">{value}</div>
      {desc && <div className="text-[10px] text-neutral-400 mt-0.5">{desc}</div>}
    </div>
  )
}
