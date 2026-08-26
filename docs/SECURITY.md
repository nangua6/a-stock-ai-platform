# 安全文档

## 绝对禁止事项

1. **API Key 写入 Git** – 所有密钥通过 `.env` 管理，`.env` 在 `.gitignore` 中
2. **券商账号密码写入代码** – 使用环境变量或 Keychain
3. **交易密码写入 Prompt** – 永远不要将凭证传给 LLM
4. **日志打印 Token/密钥** – structlog 配置中已过滤敏感字段
5. **LLM 直接调用 Broker** – 必须经过 RiskEngine + Human Confirm

## Kill Switch

- `GLOBAL_KILL_SWITCH=true` 时，所有 LIVE_ORDER 被禁止
- 仅允许查询、撤单、风险处理
- 默认开启

## 交易安全参数（默认值）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `PAPER_TRADING` | `true` | 默认模拟盘 |
| `LIVE_TRADING` | `false` | 默认关闭实盘 |
| `AUTO_TRADE` | `false` | 默认关闭自动交易 |
| `GLOBAL_KILL_SWITCH` | `true` | 默认开启 Kill Switch |
| `LIVE_ORDER_REQUIRE_CONFIRMATION` | `true` | 实盘订单需人工确认 |
| `MAX_POSITION_RATIO` | `0.20` | 单股最大仓位 20% |
| `MAX_SINGLE_TRADE_AMOUNT` | `100000` | 单笔最大 10 万 |
| `MAX_DAILY_LOSS_RATIO` | `0.03` | 单日最大亏损 3% |
| `MAX_DRAWDOWN` | `0.10` | 最大回撤 10% |
| `MAX_DAILY_ORDERS` | `20` | 单日最大订单数 |

## RBAC 权限

| 角色 | 权限 |
|------|------|
| RESEARCH | 只读分析 |
| PAPER_TRADING | 模拟交易 |
| LIVE_VIEW | 实盘查看 |
| LIVE_TRADE | 实盘交易（需确认） |
| AUTO_TRADE | 自动交易（需额外风控配置） |
| ADMIN | 全部权限 |

## 交易密钥管理

- 环境变量（开发阶段）
- 系统 Keychain（生产阶段）
- Secret Manager（云部署）
- 交易 API Credential 与 LLM Credential 必须分离

## 异常保护

| 异常场景 | 系统行为 |
|----------|----------|
| LLM API 挂掉 | 不影响账户查询 |
| 行情 API 挂掉 | 禁止新交易 |
| Broker API 挂掉 | 禁止重复下单 |
| 数据库挂掉 | 禁止 LIVE ORDER |
| Redis 挂掉 | 禁止 LIVE ORDER |

## 幂等性

所有订单使用 `client_order_id` 防止重复下单：
- 格式：`ORDER-YYYYMMDD-NNNNNN`
- 同一 ID 重复提交时系统拒绝
