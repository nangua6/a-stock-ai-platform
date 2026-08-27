/**
 * Unified API Client for A-Stock AI Platform.
 *
 * All frontend API calls go through this module.
 * Provides consistent error handling, loading states, and response parsing.
 */

import type { ApiResponse } from './types'

const BASE = '/api/v1'

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 15000,
): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!res.ok) {
      throw new ApiError(`API ${res.status}: ${res.statusText}`, res.status)
    }

    const json: ApiResponse<T> = await res.json()
    if (!json.success) {
      throw new ApiError(json.message || 'Request failed', 500)
    }
    return json.data
  } finally {
    clearTimeout(timer)
  }
}

async function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

async function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}

// ── Market API ─────────────────────────────────────────────────────────────

export const marketApi = {
  getOverview: () => get<import('./types').MarketOverview>('/market/overview'),
  getQuote: (symbol: string) => get<import('./types').QuoteData>(`/market/quote/${symbol}`),
  getQuotes: (symbols: string[]) =>
    get<import('./types').QuoteData[]>(`/market/quotes?symbols=${symbols.join(',')}`),
  getKline: (symbol: string, timeframe = 'D', limit = 100) =>
    get<import('./types').KlineBar[]>(`/market/kline/${symbol}?timeframe=${timeframe}&limit=${limit}`),
  getTechnical: (symbol: string) =>
    get<import('./types').TechnicalIndicators>(`/market/technical/${symbol}`),
  getFinancial: (symbol: string) =>
    get<import('./types').FinancialData>(`/market/financial/${symbol}`),
  getStockList: () => get<import('./types').StockListItem[]>('/market/stocks'),
  getMoneyFlow: (symbol: string) => get<Record<string, unknown>>(`/market/money-flow/${symbol}`),
  getNews: (symbol?: string) =>
    get<Record<string, unknown>[]>(`/market/news${symbol ? `?symbol=${symbol}` : ''}`),
}

// ── Analysis API ───────────────────────────────────────────────────────────

export const analysisApi = {
  analyzeStock: (symbol: string) =>
    post<import('./types').StockAnalysisResult>('/analysis/stock', { symbol }),
  analyzeMarket: () => post<Record<string, unknown>>('/analysis/market', {}),
  findCandidates: (criteria = '趋势最强', topN = 10) =>
    post<{ candidates: import('./types').ScreeningCandidate[]; total_screened: number; total_passed: number }>(
      '/analysis/candidates',
      { criteria, top_n: topN },
    ),
}

// ── Watchlist API ──────────────────────────────────────────────────────────

export const watchlistApi = {
  getAll: () => get<import('./types').WatchlistItem[]>('/watchlist'),
  add: (symbol: string, name = '') =>
    post<{ id: string; symbol: string; name: string }>(`/watchlist`, { symbol, name }),
  remove: (symbol: string) => del<{ symbol: string; removed: boolean }>(`/watchlist/${symbol}`),
  check: (symbol: string) =>
    get<import('./types').WatchlistCheckResult>(`/watchlist/${symbol}/check`),
}

// ── Backtest API ───────────────────────────────────────────────────────────

export const backtestApi = {
  run: (request: import('./types').BacktestRequest) =>
    post<import('./types').BacktestResult>('/backtest/run', request),
  getStrategies: () => get<import('./types').StrategyInfo[]>('/backtest/strategies'),
}

// ── System API ─────────────────────────────────────────────────────────────

export const systemApi = {
  getHealth: () => get<{ status: string; version: string; env: string; timestamp: string }>('/health'),
  getStatus: () => get<Record<string, unknown>>('/status'),
}

// ── Risk API ───────────────────────────────────────────────────────────────

export const riskApi = {
  getConfig: () => get<Record<string, unknown>>('/risk/config'),
  getStatus: () => get<Record<string, unknown>>('/risk/status'),
}

// ── Portfolio API ──────────────────────────────────────────────────────────

export const portfolioApi = {
  getSummary: () => get<Record<string, unknown>>('/portfolio/summary'),
}

// ── Trading API ────────────────────────────────────────────────────────────

export const tradingApi = {
  getAccount: () => get<import('./types').AccountInfo>('/trading/account'),
  getPositions: () => get<import('./types').Position[]>('/trading/positions'),
}


// ── Agent API (MiMo Investment Research) ──────────────────────────────────

export interface AgentAnalysisResponse {
  schema_version: string
  symbol: string
  name: string
  analysis_timestamp: string
  data_timestamp: string
  current_price: number | null
  change_pct: number | null
  trend: string
  technical_score: number
  fundamental_score: number
  risk_score: number
  overall_score: number
  recommendation: string
  confidence: number
  bull_case: string[]
  bear_case: string[]
  key_risks: string[]
  data_quality: string
  data_source: string
}

export interface AgentTrace {
  trace_id: string
  request_id: string
  model: string
  latency_ms: number
  tool_calls: number
  tool_call_details: Array<{
    tool: string
    status: string
    latency_ms: number
  }>
  iterations: number
  validation_result: string
  final_recommendation: string
  error: string | null
}

export interface AgentAnalyzeResult {
  data: AgentAnalysisResponse
  trace: AgentTrace
}

export const agentApi = {
  analyze: (symbol: string, question?: string) =>
    post<AgentAnalyzeResult>('/agent/analyze', { symbol, question }),
}

export { ApiError }
