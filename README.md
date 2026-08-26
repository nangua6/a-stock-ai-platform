# A股智能投研与自动化交易系统

> 以 MiMo-V2.5-Pro 为核心智能分析引擎、以量化数据和券商交易接口为执行基础、以独立风控系统约束交易行为的 A 股智能投资系统。

## 系统架构

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 技术栈

| 层 | 技术 |
|----|------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL 16, Redis 7 |
| Frontend | Next.js, TypeScript, React, Tailwind CSS |
| Charts | TradingView Lightweight Charts / ECharts |
| AI | MiMo-V2.5-Pro (OpenAI-compatible API) |
| Logging | structlog |
| Container | Docker Compose |

## 已完成功能

### 市场数据层
- **ProviderManager**: 复合数据源，自动 fallback（AkShare → Mock）
- **AkShareProvider**: 真实 A 股行情（东方财富），含重试、超时、错误处理
- **MockMarketDataProvider**: 开发/测试用模拟数据
- **MarketDataCache**: 按数据类型 TTL 缓存（quote 10s, kline 5min, financial 1h）
- **DataFreshness**: FRESH / STALE / UNAVAILABLE 三级数据新鲜度

### 技术分析
- **TechnicalAnalysisService**: MA/EMA/MACD/RSI/KDJ/Bollinger/ATR/波动率/量比

### 交易策略（6 个）
- **MACDStrategy**: MACD 金叉/死叉
- **MACrossStrategy**: 均线交叉（可配参数）
- **RSIStrategy**: RSI 超买超卖
- **MomentumStrategy**: ROC + RSI + MA 趋势动量
- **BollingerStrategy**: 布林带均值回归
- **ValueStrategy**: PE/PB/ROE 基本面估值

### AI 分析
- **StockAnalysisAgent**: 确定性评分 + 结构化输出
  - `Recommendation`: WATCH / BUY_CANDIDATE / HOLD / REDUCE / AVOID / DATA_UNAVAILABLE
  - 技术评分、风险评估、bull/bear case
  - 不依赖 LLM 可独立运行
- **MarketContextBuilder**: AI 上下文构建器（缺失数据显式标记 UNAVAILABLE）
- **ScreeningEngine**: 结构化因子选股

### 风控系统
- **RiskEngine**: 18 项检查

### 数据持久化层
- **Database**: PostgreSQL 16 + SQLAlchemy async ORM
- **Models**: User, Account, Stock, Kline, Order, Trade, Position, Signal, DataSyncJob, TechnicalSnapshot, AnalysisSnapshot
- **Repository**: 统一 CRUD + upsert 幂等
- **MarketDataService**: Provider → DB 持久化桥接
- **SyncService**: 完整数据同步管线（stock_list → kline → technical → analysis）
- **DataQualityService**: 写入前数据校验（symbol/price/volume/timestamp）
- **Scheduler**: asyncio 定时任务（可配置 interval + 交易日历）
- **Alembic**: 数据库 migration 管理
  - Kill Switch、交易模式、手数、价格、涨跌停保护
  - 仓位限制、资金检查、单笔限额
  - 行业暴露限制、连续亏损冷却期
  - 数据新鲜度保护、数据可用性检查
  - 每日亏损、最大回撤
- LLM **无权**覆盖 RiskEngine

### 交易执行
- **PaperBroker**: 模拟 A 股规则（T+1、佣金、印花税、滑点）
- **MockBroker**: 开发测试用
- **TradingService**: 订单 → 风控 → 执行 → 审计

### 回测引擎
- **BacktestEngine**: 支持佣金、印花税、滑点、T+1

### API 端点
| 端点 | 说明 |
|------|------|
| `GET /market/quote/{symbol}` | 实时行情 |
| `GET /market/kline/{symbol}` | K 线数据 |
| `GET /market/technical/{symbol}` | 技术指标 |
| `GET /market/overview` | 市场概览 |
| `GET /market/data-status` | 数据源健康状态 |
| `POST /analysis/stock` | 结构化股票分析 |
| `POST /analysis/candidates` | 选股筛选 |
| `POST /trading/order` | 下单（Paper/Live） |
| `GET /risk/config` | 风控配置 |
| `GET /risk/status` | 风控运行状态 |
| `POST /risk/cooldown/reset` | 重置冷却期 |
| `POST /backtest/run` | 运行回测 |

## 快速开始

### 前置条件

- Python 3.12+
- Docker & Docker Compose

### 1. 克隆仓库

```bash
git clone https://github.com/nangua6/a-stock-ai-platform.git
cd a-stock-ai-platform
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 3. 启动后端

```bash
# 启动 PostgreSQL
docker compose up -d postgres

# 执行数据库 migration
cd backend
source .venv/bin/activate
alembic upgrade head

# 启动 API 服务
uvicorn app.main:app --reload --port 8000
```

### 4. 运行测试
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. 运行测试

```bash
cd backend
source .venv/bin/activate
# 单元测试（无需网络和数据库）
pytest tests/ --ignore=tests/integration -v
# PostgreSQL 集成测试（需要 docker compose up -d postgres）
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/astock_ai_test \
  pytest tests/integration/test_postgres_persistence.py -v -m integration
# AkShare 集成测试（需要真实网络）
pytest tests/integration/test_akshare_integration.py -v -m integration
```

### 5. 访问 API

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/v1/health

## 运行模式

| 模式 | 说明 | 默认 |
|------|------|------|
| Research | 纯研究，禁止交易 | - |
| Paper Trading | 模拟交易 | ✅ |
| Live Trading | 真实交易（需手动开启） | ❌ |

## MiMo AI 配置

```bash
MIMO_API_KEY=your_key_here
MIMO_BASE_URL=https://api.mimo.com/v1
MIMO_MODEL=mimo-v2.5-pro
```

## 安全提示

⚠️ **本系统涉及真实资金交易，请务必：**

1. 充分理解风险后再启用 LIVE Trading
2. 先在 Paper Trading 模式下验证策略
3. 初始阶段使用极小金额
4. 永远保持 Kill Switch 可用
5. 不要将 API Key 和券商凭证提交到 Git

## 项目状态

当前处于 **Phase 3** — 数据持久化基础设施已完成。

- ✅ 市场数据层（ProviderManager + AkShare + Mock + Cache）
- ✅ 技术分析服务（16 个指标）
- ✅ 6 个量化策略
- ✅ AI 结构化分析 Agent
- ✅ 选股引擎
- ✅ 风控系统（18 项检查）
- ✅ 回测引擎
- ✅ 数据库持久化（PostgreSQL + Repository + SyncService）
- ✅ Alembic migration
- ✅ Scheduler 定时同步
- ✅ 数据质量校验
- ✅ 215 个单元测试 + PostgreSQL 集成测试

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 了解完整开发计划。

## 许可证

Private – All rights reserved.
| `GET /data/status` | 数据源健康状态 |
| `GET /data/sync/status` | 同步任务状态 |
| `GET /data/sync/history` | 同步历史 |
| `POST /data/sync/stock-list` | 触发股票列表同步 |
| `POST /data/sync/klines` | 触发 K 线同步 |
| `POST /data/sync/technical` | 触发技术指标计算 |
| `POST /data/sync/analysis` | 触发分析快照 |
| `POST /data/sync/full` | 触发完整管线 |
| `GET /data/scheduler/status` | 调度器状态 |

## Scheduler 配置

Scheduler 默认关闭，通过环境变量启用：

```bash
# 启用 Scheduler
SCHEDULER_ENABLED=true

# 配置同步间隔（秒）
SCHEDULER_STOCK_LIST_INTERVAL=86400   # 股票列表同步（24h）
SCHEDULER_KLINE_INTERVAL=3600         # K 线同步（1h）
SCHEDULER_KLINE_BATCH_SIZE=50         # 每批最大股票数
```

### 生产环境注意事项

- Scheduler 默认关闭，需手动启用
- 多 worker 部署时（`uvicorn --workers > 1`），需确保只启动一个 scheduler 实例
- Scheduler 使用 `EnhancedTradingCalendar` 判断交易日，跳过周末和节假日
- 交易日历 provider 可插拔，默认使用周末 fallback
- 单只股票同步失败不影响整个批次

## 数据库

### 本地开发

```bash
# 启动 PostgreSQL
docker compose up -d postgres

# 执行 migration
cd backend
source .venv/bin/activate
alembic upgrade head

# 连接配置（默认）
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/astock_ai
```

### 测试数据库

```bash
# 创建测试数据库
createdb astock_ai_test

# 运行 PostgreSQL 集成测试
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/astock_ai_test \
  pytest tests/integration/test_postgres_persistence.py -v -m integration
```
