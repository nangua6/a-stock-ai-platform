'use client'

import { useEffect, useState, useCallback } from 'react'
import { backtestApi } from '@/lib/api'
import type { StrategyInfo, BacktestResult, BacktestRequest, DataMeta } from '@/lib/types'
import { DataStateBanner } from '@/components/DataState'
import { MockBadge } from '@/components/MockBadge'
import { formatPct, formatPrice, changeColor, scoreColor } from '@/lib/utils'
import { EquityCurveChart } from '@/components/EquityCurveChart'

export default function StrategyPage() {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([])
  const [selected, setSelected] = useState('')
  const [symbol, setSymbol] = useState('600519.SH')
  const [startDate, setStartDate] = useState('2025-01-01')
  const [endDate, setEndDate] = useState('2026-08-25')
  const [capital, setCapital] = useState(1000000)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [meta, setMeta] = useState<DataMeta>({ state: 'LOADING' })
  const [runMeta, setRunMeta] = useState<DataMeta>({ state: 'SUCCESS' })

  useEffect(() => {
    backtestApi.getStrategies().then(data => {
      setStrategies(data)
      if (data.length > 0) setSelected(data[0].key)
      setMeta({ state: 'SUCCESS' })
    }).catch(err => {
      setMeta({ state: 'ERROR', error: err.message })
    })
  }, [])

  const handleRun = useCallback(async () => {
    if (!selected) return
    setRunning(true)
    setRunMeta({ state: 'LOADING' })
    setResult(null)
    try {
      const req: BacktestRequest = {
        strategy: selected,
        symbols: symbol.split(',').map(s => s.trim()),
        start_date: startDate,
        end_date: endDate,
        initial_capital: capital,
      }
      const data = await backtestApi.run(req)
      setResult(data)
      setRunMeta({ state: 'SUCCESS', source: data.data_source })
    } catch (err) {
      setRunMeta({ state: 'ERROR', error: err instanceof Error ? err.message : 'Backtest failed' })
    } finally {
      setRunning(false)
    }
  }, [selected, symbol, startDate, endDate, capital])

  return (
    <div className="page-container">
      <div>
        <h1>策略中心</h1>
        <p className="text-sm text-neutral-500 mt-1">
          量化策略回测与分析
        </p>
      </div>

      <DataStateBanner meta={meta} />

      {/* Strategy Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {strategies.map(s => (
          <button
            key={s.key}
            className={`card text-left transition-all ${selected === s.key ? 'ring-2 ring-blue-500 border-blue-300' : 'hover:border-neutral-300'}`}
            onClick={() => setSelected(s.key)}
          >
            <div className="card-header flex items-center justify-between">
              <span className="font-bold">{s.name}</span>
              <span className="badge bg-neutral-100 text-neutral-600">{s.type}</span>
            </div>
            <div className="card-body">
              <p className="text-sm text-neutral-600 mb-2">{s.desc}</p>
              <div className="text-xs text-neutral-400">适用周期: {s.period}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Backtest Configuration */}
      <div className="card">
        <div className="card-header">回测配置</div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
            <div>
              <label className="text-xs text-neutral-500 block mb-1">股票代码</label>
              <input
                type="text"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm"
                value={symbol}
                onChange={e => setSymbol(e.target.value)}
                placeholder="600519.SH"
              />
            </div>
            <div>
              <label className="text-xs text-neutral-500 block mb-1">开始日期</label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-neutral-500 block mb-1">结束日期</label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-neutral-500 block mb-1">初始资金</label>
              <input
                type="number"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm font-mono"
                value={capital}
                onChange={e => setCapital(Number(e.target.value))}
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              className="btn-primary"
              onClick={handleRun}
              disabled={running || !selected}
            >
              {running ? '回测中...' : '开始回测'}
            </button>
            {selected && (
              <span className="text-sm text-neutral-500">
                策略: {strategies.find(s => s.key === selected)?.name || selected}
              </span>
            )}
          </div>
        </div>
      </div>

      <DataStateBanner meta={runMeta} />

      {/* Backtest Results */}
      {result && <BacktestResultPanel result={result} />}
    </div>
  )
}

function BacktestResultPanel({ result }: { result: BacktestResult }) {
  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <span>回测结果 · {result.strategy_name}</span>
          <MockBadge source={result.data_source} />
        </div>
        <div className="card-body">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              label="总收益率"
              value={formatPct(result.total_return * 100)}
              color={changeColor(result.total_return)}
            />
            <MetricCard
              label="年化收益"
              value={formatPct(result.annualized_return * 100)}
              color={changeColor(result.annualized_return)}
            />
            <MetricCard
              label="最大回撤"
              value={formatPct(-result.max_drawdown * 100)}
              color="text-red-600"
            />
            <MetricCard
              label="Sharpe"
              value={result.sharpe_ratio != null ? result.sharpe_ratio.toFixed(4) : '—'}
            />
            <MetricCard
              label="胜率"
              value={formatPct(result.win_rate * 100)}
            />
            <MetricCard
              label="盈亏比"
              value={result.profit_factor.toFixed(2)}
            />
            <MetricCard
              label="总交易数"
              value={String(result.total_trades)}
            />
            <MetricCard
              label="最终资金"
              value={formatPrice(result.final_capital)}
            />
          </div>
        </div>
      </div>

      {/* Equity Curve */}
      {result.equity_curve.length > 0 && (
        <div className="card">
          <div className="card-header">资金曲线</div>
          <div className="card-body p-2">
            <EquityCurveChart
              data={result.equity_curve}
              initialCapital={result.initial_capital}
            />
          </div>
        </div>
      )}

      {/* Trade List */}
      {result.trades.length > 0 && (
        <div className="card">
          <div className="card-header">交易明细 ({result.trades.length})</div>
          <div className="overflow-x-auto max-h-80 overflow-y-auto">
            <table className="w-full">
              <thead className="sticky top-0 bg-white">
                <tr className="text-xs text-neutral-500 border-b border-neutral-100">
                  <th className="text-left table-cell font-medium">日期</th>
                  <th className="text-center table-cell font-medium">方向</th>
                  <th className="text-right table-cell font-medium">价格</th>
                  <th className="text-right table-cell font-medium">数量</th>
                  <th className="text-right table-cell font-medium">金额</th>
                  <th className="text-right table-cell font-medium">手续费</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.map((t, i) => (
                  <tr key={i} className="border-b border-neutral-50 text-sm">
                    <td className="table-cell font-mono text-xs">{t.trade_date}</td>
                    <td className="table-cell text-center">
                      <span className={`badge ${t.side === 'BUY' ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
                        {t.side === 'BUY' ? '买入' : '卖出'}
                      </span>
                    </td>
                    <td className="table-cell text-right font-mono">{formatPrice(t.price)}</td>
                    <td className="table-cell text-right font-mono">{t.quantity}</td>
                    <td className="table-cell text-right font-mono">{formatPrice(t.amount)}</td>
                    <td className="table-cell text-right font-mono text-xs text-neutral-500">{formatPrice(t.commission)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="p-3 bg-neutral-50 rounded-lg">
      <div className="text-xs text-neutral-500 mb-1">{label}</div>
      <div className={`text-base font-bold font-mono tabular-nums ${color || 'text-neutral-800'}`}>
        {value}
      </div>
    </div>
  )
}
