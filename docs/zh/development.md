# 开发指南

## 工作原则

- 保持项目工作流逻辑和知识入库逻辑分离。
- 除非明确要改产品行为，否则维持 `bible -> outline -> draft` 的流转模型。
- 重构或行为改动前优先补测试。
- API 契约以 `src/scriptwriter/api/routers/projects.py` 为准。

## 本地开发流程

1. 安装依赖：

```bash
uv sync
```

2. 运行测试：

```bash
uv run pytest -q
```

3. 运行静态检查：

```bash
uv run --extra dev ruff check src tests
```

4. 启动 API 做手工验证：

```bash
PYTHONPATH=src uv run uvicorn scriptwriter.api.app:app --reload
```

## 测试目录

- `tests/scriptwriter/api/`：API 契约行为
- `tests/scriptwriter/projects/`：项目服务与仓库行为
- `tests/scriptwriter/workflow/`：工作流状态流转
- `tests/scriptwriter/knowledge/`：入库与检索行为
- `tests/scriptwriter/tools/builtins/`：工具级行为
- `tests/scriptwriter/memory/`：内存快照行为

## 常见改动模式

### 新增或修改 API 接口

1. 修改 `src/scriptwriter/api/routers/projects.py`，或在 `src/scriptwriter/api/routers/` 下新增 router。
2. 如有需要，在 `src/scriptwriter/api/app.py` 注册新 router。
3. 在 `tests/scriptwriter/api/` 下新增或修改测试。
4. 同步更新 `docs/en/api-reference.md` 和 `docs/zh/api-reference.md`。

### 修改工作流逻辑

1. 在 `src/scriptwriter/projects/workflow.py` 修改状态流转。
2. 在 `src/scriptwriter/projects/service.py` 和 `src/scriptwriter/agent/service.py` 修改编排与动作判定。
3. 在 `tests/scriptwriter/projects/` 与 `tests/scriptwriter/workflow/` 中补充或调整测试。
4. 若用户可见流程发生变化，同时更新 README 和架构文档。

### 修改知识库行为

1. 修改 `src/scriptwriter/knowledge/service.py`。
2. 按需要修改 `metadata_store_pg.py`、`keyword_store.py`、`milvus_store.py`、`embeddings.py` 等支持模块。
3. 在 `tests/scriptwriter/knowledge/` 中补充或调整测试。
4. 若环境变量、存储路径或作用域语义变化，同时更新运维与安全文档。

## 文档规则

当行为、接口或环境变量发生变化时，至少同步更新：

- `README.md`
- `README_ZH.md`
- `docs/en/` 下至少一份详细文档
- `docs/zh/` 下对应的中文文档
