// ── Market Data Types ──────────────────────────────────────────────────────

export interface MarketIndex {
  name: string
  code?: string
  price: number
  change_pct: number
  volume?: number
  amount?: number
  timestamp?: string
}

export interface MarketOverview {
  indices: Record<string, { price: number; change_pct: number }>
  up_count: number
  down_count: number
  limit_up_count: number
  limit_down_count: number
  total_amount: number
  northbound_flow?: number
  timestamp: string
  data_source: string
}

export interface QuoteData {
  symbol: string
  name: string
  price: number
  open: number
  high: number
  low: number
  pre_close: number
  volume: number
  amount: number
  change: number
  change_pct: number
  bid1_price: number
  ask1_price: number
  bid1_volume: number
  ask1_volume: number
  timestamp: string
  data_source: string
}

export interface KlineBar {
  symbol: string
  trade_date: string
  timeframe: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
  change_pct: number
  data_source: string
}

export interface FinancialData {
  symbol: string
  report_date: string
  revenue: number
  net_profit: number
  eps: number
  roe: number
  pe_ratio: number
  pb_ratio: number
  market_cap: number
  total_share: number
  data_source: string
}

// ── Technical Indicators ───────────────────────────────────────────────────

export interface TechnicalIndicators {
  symbol: string
  ma5: number
  ma10: number
  ma20: number
  ma60: number
  ema12: number
  ema26: number
  macd_line: number
  macd_signal: number
  macd_histogram: number
  rsi: number
  kdj_k: number
  kdj_d: number
  kdj_j: number
  boll_upper: number
  boll_middle: number
  boll_lower: number
  atr: number
  volume_ma5: number
  volume_ma10: number
  volume_ma20: number
  volatility: number
  turnover_rate: number
  amplitude: number
  computed_at: string
  period: number
}

// ── AI Analysis ────────────────────────────────────────────────────────────

export interface TechnicalScore {
  trend: string
  momentum: number
  volume_signal: number
  ma_alignment: number
  rsi_signal: number
  macd_signal: number
  score: number
}

export interface RiskAssessment {
  volatility: number
  max_drawdown: number
  data_age_seconds: number
  is_data_fresh: boolean
  risk_level: string
  key_risks: string[]
}

export interface StockAnalysisResult {
  symbol: string
  name: string
  analysis_timestamp: string
  data_timestamp: string
  current_price: number | null
  change_pct: number | null
  volume: number | null
  amount: number | null
  technical: TechnicalScore
  fundamental_score: number
  risk: RiskAssessment
  overall_score: number
  recommendation: string
  confidence: number
  bull_case: string
  bear_case: string
  key_risks: string[]
  data_quality: string
  data_source: string
}

// ── Stock List ─────────────────────────────────────────────────────────────

export interface StockListItem {
  symbol: string
  name: string
  industry: string
  market: string
}

// ── Screening ──────────────────────────────────────────────────────────────

export interface ScreeningCandidate {
  symbol: string
  name: string
  score: number
  factors: Record<string, number>
  matched_rules: string[]
}

// ── Trading ────────────────────────────────────────────────────────────────

export interface AccountInfo {
  account_id: string
  total_asset: number
  cash: number
  market_value: number
  available_cash: number
}

export interface Position {
  symbol: string
  name: string
  quantity: number
  avg_cost: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
}

// ── API Response ───────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

// ── Data State ─────────────────────────────────────────────────────────────

export type DataState = 'LOADING' | 'SUCCESS' | 'STALE' | 'UNAVAILABLE' | 'ERROR'

export interface DataMeta {
  state: DataState
  timestamp?: string
  source?: string
  dataAge?: string
  error?: string
}

// ── Watchlist ──────────────────────────────────────────────────────────────

export interface WatchlistItem {
  id: string
  symbol: string
  name: string
  note: string | null
  created_at: string | null
  quote: {
    price: number
    change_pct: number
    volume: number
    amount: number
    timestamp: string
    data_source: string
  } | null
}

export interface WatchlistCheckResult {
  symbol: string
  in_watchlist: boolean
}

// ── Backtest ───────────────────────────────────────────────────────────────

export interface BacktestRequest {
  strategy: string
  symbols: string[]
  start_date: string
  end_date: string
  initial_capital: number
  commission_rate?: number
  slippage_rate?: number
}

export interface BacktestTrade {
  symbol: string
  side: string
  price: number
  quantity: number
  amount: number
  commission: number
  trade_date: string
  strategy: string
  signal_strength: number
}

export interface BacktestResult {
  strategy_name: string
  start_date: string
  end_date: string
  initial_capital: number
  final_capital: number
  total_return: number
  annualized_return: number
  sharpe_ratio: number | null
  max_drawdown: number
  win_rate: number
  profit_factor: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  avg_win: number
  avg_loss: number
  trades: BacktestTrade[]
  equity_curve: { date: string; equity: number }[]
  data_source: string
}

export interface StrategyInfo {
  key: string
  name: string
  type: string
  desc: string
  period: string
}
