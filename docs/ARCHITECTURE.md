# A股智能投研平台 – 系统架构

## 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                     │
│         Dashboard / Stock Detail / Trading / AI           │
└────────────────────────┬────────────────────────────────┘
                         │ REST / WebSocket
┌────────────────────────┴────────────────────────────────┐
│                   Backend (FastAPI)                       │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │   API   │ │ Services │ │ Agents   │ │  Scheduler  │  │
│  │  Layer  │ │  Layer   │ │  Layer   │ │   (APSch)   │  │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └─────────────┘  │
│       │           │             │                         │
│  ┌────┴───────────┴─────────────┴──────────────────────┐ │
│  │              Core Business Logic                      │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │ │
│  │  │ Strategy │ │  Risk    │ │ Portfolio│            │ │
│  │  │  Engine  │ │  Engine  │ │  Engine  │            │ │
│  │  └──────────┘ └──────────┘ └──────────┘            │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │ │
│  │  │ Backtest │ │  Trade   │ │  Audit   │            │ │
│  │  │  Engine  │ │ Service  │ │  Logger  │            │ │
│  │  └──────────┘ └──────────┘ └──────────┘            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            AI Layer (MiMo + Agents)               │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │   │
│  │  │   LLM    │ │  Agent   │ │   Tool Registry  │ │   │
│  │  │  Client  │ │ Orchestr.│ │   (MCP-style)    │ │   │
│  │  └──────────┘ └──────────┘ └──────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Data & Broker Adapters                    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │   │
│  │  │ Market   │ │ Broker   │ │   Data Source    │ │   │
│  │  │ Provider │ │ Adapter  │ │   Fallback Chain │ │   │
│  │  └──────────┘ └──────────┘ └──────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────┴────┐    ┌─────┴─────┐   ┌─────┴─────┐
    │PostgreSQL│    │   Redis   │   │  Broker   │
    │  (async) │    │ (cache)   │   │  (QMT/    │
    │          │    │           │   │  PTrade)  │
    └─────────┘    └───────────┘   └───────────┘
```

## 关键设计原则

### 1. LLM 不能直接调用 Broker API

```
MiMo → ChiefAgent → Strategy → Risk Engine → Trade Proposal → Human Confirm → Broker
```

### 2. 三种运行模式

| 模式 | 交易 | 风控 | 适用场景 |
|------|------|------|----------|
| Research | 禁止 | 无 | 纯研究分析 |
| Paper | 模拟 | 完整 | 策略验证 |
| Live | 真实 | 完整+人工确认 | 实盘交易 |

### 3. 确定性计算 vs LLM 推理

| 层 | 职责 | 实现 |
|----|------|------|
| 技术指标 | MA, MACD, RSI, BOLL... | Pandas/NumPy |
| 风控检查 | 所有风险规则 | 确定性代码 |
| 回测引擎 | 策略回测 | 确定性代码 |
| 交易执行 | 下单、撤单 | 确定性代码 |
| AI 分析 | 综合分析、推理、解释 | LLM |
| 策略生成 | 策略建议 | LLM + 回测验证 |

### 4. RBAC 权限

```
ADMIN > AUTO_TRADE > LIVE_TRADE > LIVE_VIEW > PAPER_TRADING > RESEARCH
```

### 5. 审计追踪链

```
User → Agent → Tool → Strategy → Risk → TradeProposal → Confirmation → Broker → Order → Trade
```

## 技术栈

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL 16 (async), Redis 7
- **Frontend**: Next.js, TypeScript, React, Tailwind CSS
- **Charts**: TradingView Lightweight Charts / ECharts
- **AI**: MiMo-V2.5-Pro (OpenAI-compatible API)
- **Task Queue**: APScheduler
- **Logging**: structlog
- **Containerization**: Docker Compose

## 开发阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| PHASE 0 | 需求与架构设计 | ✅ |
| PHASE 1 | 项目骨架 | ✅ |
| PHASE 2 | 数据库 | 🔄 |
| PHASE 3 | 行情数据 | ⏳ |
| PHASE 4 | 技术指标 | ⏳ |
| PHASE 5 | 策略引擎 | ⏳ |
| PHASE 6 | 回测 | ⏳ |
| PHASE 7 | AI Agent | ⏳ |
| PHASE 8 | Dashboard | ⏳ |
| PHASE 9 | Paper Trading | ⏳ |
| PHASE 10 | Risk Engine | ⏳ |
| PHASE 11 | Broker Adapter | ⏳ |
| PHASE 12 | LIVE View | ⏳ |
| PHASE 13 | LIVE Trading | ⏳ |
