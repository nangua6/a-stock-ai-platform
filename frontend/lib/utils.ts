/**
 * Formatting utilities for A-stock data display.
 */

export function formatPrice(price: number | null | undefined): string {
  if (price == null || isNaN(price)) return '—'
  return price.toFixed(2)
}

export function formatPct(pct: number | null | undefined): string {
  if (pct == null || isNaN(pct)) return '—'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

export function formatAmount(amount: number | null | undefined): string {
  if (amount == null || isNaN(amount)) return '—'
  if (amount >= 1e12) return `${(amount / 1e12).toFixed(2)}万亿`
  if (amount >= 1e8) return `${(amount / 1e8).toFixed(2)}亿`
  if (amount >= 1e4) return `${(amount / 1e4).toFixed(2)}万`
  return amount.toFixed(2)
}

export function formatVolume(vol: number | null | undefined): string {
  if (vol == null || isNaN(vol)) return '—'
  if (vol >= 1e8) return `${(vol / 1e8).toFixed(2)}亿`
  if (vol >= 1e4) return `${(vol / 1e4).toFixed(0)}万`
  return vol.toLocaleString()
}

export function formatLargeNum(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '—'
  if (Math.abs(n) >= 1e12) return `${(n / 1e12).toFixed(2)}万亿`
  if (Math.abs(n) >= 1e8) return `${(n / 1e8).toFixed(2)}亿`
  if (Math.abs(n) >= 1e4) return `${(n / 1e4).toFixed(2)}万`
  return n.toLocaleString()
}

export function changeColor(value: number | null | undefined): string {
  if (value == null || value === 0) return 'text-neutral-500'
  return value > 0 ? 'text-up' : 'text-down'
}

export function changeBg(value: number | null | undefined): string {
  if (value == null || value === 0) return 'bg-neutral-100'
  return value > 0 ? 'bg-red-50' : 'bg-green-50'
}

export function scoreColor(score: number): string {
  if (score >= 70) return 'text-up'
  if (score >= 50) return 'text-amber-600'
  return 'text-down'
}

export function riskLevelColor(level: string): string {
  switch (level) {
    case 'LOW': return 'text-green-600 bg-green-50'
    case 'MEDIUM': return 'text-amber-600 bg-amber-50'
    case 'HIGH': return 'text-red-600 bg-red-50'
    case 'EXTREME': return 'text-red-700 bg-red-100'
    default: return 'text-neutral-500 bg-neutral-100'
  }
}

export function recommendationColor(rec: string): string {
  switch (rec) {
    case 'BUY_CANDIDATE': return 'text-up bg-red-50 border-red-200'
    case 'WATCH': return 'text-amber-600 bg-amber-50 border-amber-200'
    case 'HOLD': return 'text-blue-600 bg-blue-50 border-blue-200'
    case 'REDUCE': return 'text-orange-600 bg-orange-50 border-orange-200'
    case 'AVOID': return 'text-down bg-green-50 border-green-200'
    default: return 'text-neutral-500 bg-neutral-50 border-neutral-200'
  }
}

export function recommendationLabel(rec: string): string {
  switch (rec) {
    case 'BUY_CANDIDATE': return '关注买入'
    case 'WATCH': return '观望'
    case 'HOLD': return '持有'
    case 'REDUCE': return '减仓'
    case 'AVOID': return '回避'
    case 'DATA_UNAVAILABLE': return '数据不可用'
    default: return rec
  }
}

export function trendLabel(trend: string): string {
  switch (trend) {
    case 'STRONG_UP': return '强势上涨'
    case 'UP': return '上涨'
    case 'SIDEWAYS': return '震荡'
    case 'DOWN': return '下跌'
    case 'STRONG_DOWN': return '强势下跌'
    default: return trend
  }
}

export function isMockData(source: string): boolean {
  return source === 'mock'
}
