# 开发假设记录

## 已确认假设

1. **开发环境**: macOS Apple Silicon (ARM64)
2. **Python 版本**: 3.12+ (Homebrew)
3. **Node.js 版本**: 26.x (Homebrew)
4. **Docker**: Docker Desktop 29.x
5. **数据库**: PostgreSQL 16 via Docker
6. **缓存**: Redis 7 via Docker
7. **LLM API**: MiMo-V2.5-Pro (OpenAI-compatible endpoint)

## 待确认假设

1. **数据源**: 假设使用 Tushare 作为主数据源，需要用户确认 API Key
2. **券商接入**: 第一阶段使用 Mock/Paper，不接入真实券商
3. **MiMo API**: 假设 MiMo API 兼容 OpenAI Chat Completions 格式
4. **交易费用**: 使用默认费率（万三佣金、万五印花税）
5. **用户认证**: 第一阶段不实现完整用户系统

## 风险标记

- MiMo API 的具体调用格式可能需要根据实际文档调整
- QMT/PTrade SDK 需要在实际开户后才能确认接口
- 数据源 API 限制（频率、数据范围）需要实际测试
