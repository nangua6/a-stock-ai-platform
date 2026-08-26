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

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose

### 1. 克隆仓库

```bash
git clone <repo-url>
cd a-stock-ai-platform
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 3. 启动基础设施

```bash
docker compose up -d postgres redis
```

### 4. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. 访问 API

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/v1/health
- 系统状态: http://localhost:8000/api/v1/status

### 6. 启动前端（开发中）

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

## 运行模式

| 模式 | 说明 | 默认 |
|------|------|------|
| Research | 纯研究，禁止交易 | - |
| Paper Trading | 模拟交易 | ✅ |
| Live Trading | 真实交易（需手动开启） | ❌ |

## MiMo AI 配置

在 `.env` 中配置：

```bash
MIMO_API_KEY=your_key_here
MIMO_BASE_URL=https://api.mimo.com/v1
MIMO_MODEL=mimo-v2.5-pro
```

系统通过 OpenAI-compatible 抽象层调用 MiMo，不将 API 调用散落在项目各处。

## 行情数据配置

支持多数据源自动降级：

```bash
MARKET_DATA_PROVIDER=tushare
MARKET_DATA_API_KEY=your_key_here
```

## Paper Trading

默认使用 Paper Trading 模式，模拟 A 股交易规则：

- T+1 限制
- 涨跌停限制
- 最小交易单位（100 股/手）
- 佣金、印花税、过户费
- 滑点模拟

## 风险控制

详见 [docs/SECURITY.md](docs/SECURITY.md)

- 全局 Kill Switch
- 单股最大仓位限制
- 单日最大亏损限制
- 最大回撤限制
- 所有 LIVE 订单需人工确认

## 安全提示

⚠️ **本系统涉及真实资金交易，请务必：**

1. 充分理解风险后再启用 LIVE Trading
2. 先在 Paper Trading 模式下验证策略
3. 初始阶段使用极小金额
4. 永远保持 Kill Switch 可用
5. 不要将 API Key 和券商凭证提交到 Git

## 项目状态

当前处于 **PHASE 1** – 项目骨架已完成。

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 了解完整开发计划。

## 许可证

Private – All rights reserved.
