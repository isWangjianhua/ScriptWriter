# 开发指南

## 开发原则

- 严格保持 thread 与租户边界（`thread_id`、`user_id`、`project_id`）。
- 保持 RAG 与运行状态职责分离。
- 变更行为优先补测试。
- 事件与快照必须可 JSON 序列化。

## 本地开发流程

1. 安装依赖：

```bash
uv sync
```

2. 跑测试：

```bash
uv run pytest -q
```

3. 跑 lint：

```bash
uv run --extra dev ruff check src tests
```

4. 启动 API：

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.gateway.app:app --reload
```

## 测试目录说明

- `tests/scriptwriter/gateway/routers/`：API 与安全行为
- `tests/scriptwriter/agents/`：编排与状态逻辑
- `tests/scriptwriter/state_store/`：存储层协议
- `tests/scriptwriter/rag/`：切分、元数据与检索
- `tests/scriptwriter/tools/builtins/`：工具契约

## 常见变更路径

### 新增 API

1. 在 `src/scriptwriter/gateway/routers/` 添加路由
2. 在 `gateway/app.py` 注册
3. 在 `tests/scriptwriter/gateway/routers/` 添加测试
4. 更新 `docs/*/api-reference.md`

### 修改 Agent State

1. 更新 `agents/thread_state.py`
2. 更新 orchestrator 的合并与恢复逻辑
3. 如有需要更新序列化逻辑
4. 更新对应测试

### 修改 State Store 协议

1. 先改 `state_store/base.py`
2. 同步改 `in_memory.py` 与 `postgres.py`
3. 补协议一致性测试

## 文档更新规则

当 API、环境变量、行为变更时，至少同步更新：

- `README.md` / `README_ZH.md`
- `docs/en/*` 与 `docs/zh/*` 对应文档
