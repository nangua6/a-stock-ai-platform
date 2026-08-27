'use client'

import { useEffect, useState } from 'react'
import { systemApi, riskApi } from '@/lib/api'

export default function SystemPage() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [riskConfig, setRiskConfig] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    systemApi.getHealth().then(setHealth).catch(() => {})
    systemApi.getStatus().then(setStatus).catch(() => {})
    riskApi.getConfig().then(setRiskConfig).catch(() => {})
  }, [])

  return (
    <div className="page-container">
      <div>
        <h1>系统管理</h1>
        <p className="text-sm text-neutral-500 mt-1">
          系统状态 · 风控配置 · 数据同步
        </p>
      </div>

      {/* System Health */}
      <div className="card">
        <div className="card-header">系统状态</div>
        <div className="card-body">
          {health ? (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <InfoField label="状态" value={String(health.status)} />
              <InfoField label="版本" value={String(health.version)} />
              <InfoField label="环境" value={String(health.env)} />
              <InfoField label="时间" value={new Date(String(health.timestamp)).toLocaleString('zh-CN')} />
            </div>
          ) : (
            <div className="text-sm text-neutral-400">加载中...</div>
          )}
        </div>
      </div>

      {/* Trading Status */}
      <div className="card">
        <div className="card-header">交易状态</div>
        <div className="card-body">
          {status ? (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              <InfoField label="交易模式" value={String(status.trading_mode)} />
              <InfoField
                label="Kill Switch"
                value={status.kill_switch ? 'ACTIVATED' : 'OFF'}
                danger={!!status.kill_switch}
              />
              <InfoField label="自动交易" value={String(status.auto_trade)} />
              <InfoField label="市场阶段" value={String(status.market_phase)} />
              <InfoField label="数据源" value={String(status.market_data_provider)} />
              <InfoField label="券商" value={String(status.broker_provider)} />
            </div>
          ) : (
            <div className="text-sm text-neutral-400">加载中...</div>
          )}
        </div>
      </div>

      {/* Risk Config */}
      <div className="card">
        <div className="card-header">风控参数</div>
        <div className="card-body">
          {riskConfig ? (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(riskConfig).map(([k, v]) => (
                <InfoField key={k} label={formatLabel(k)} value={formatValue(v)} />
              ))}
            </div>
          ) : (
            <div className="text-sm text-neutral-400">加载中...</div>
          )}
        </div>
      </div>
    </div>
  )
}

function InfoField({
  label,
  value,
  danger,
}: {
  label: string
  value: string
  danger?: boolean
}) {
  return (
    <div className="p-2.5 bg-neutral-50 rounded-md">
      <div className="text-xs text-neutral-500 mb-0.5">{label}</div>
      <div className={`text-sm font-mono font-medium ${danger ? 'text-red-600' : 'text-neutral-800'}`}>
        {value}
      </div>
    </div>
  )
}

function formatLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatValue(v: unknown): string {
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  if (typeof v === 'number') return String(v)
  return String(v)
}
