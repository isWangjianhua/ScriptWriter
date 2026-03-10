# 安全模型

## 范围

当前安全能力比较基础，主要包括：

- 通过 Pydantic 做请求体验证
- 在工作流和知识接口上校验项目是否存在
- 通过 `user_id` 和 `project_id` 做知识数据作用域过滤
- 将知识原文限制在 `data/rag/` 目录下持久化

这还不是完整的认证和授权系统。

## API 边界

当前接口全部是 project-scoped：

- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/chat`
- `POST /api/projects/{project_id}/confirm`
- `POST /api/projects/{project_id}/knowledge/upload`
- `GET /api/projects/{project_id}/versions`

当前实现不存在 thread 边界。

## 校验边界

请求体通过 Pydantic 保证以下字段非空：

- `project_id`、`title`、`message`
- 知识上传里的 `user_id`、`content`、`doc_type`

知识入库还会额外限制 `doc_type` 必须属于：

- `script`
- `novel`
- `text`
- `markdown`

## 知识作用域隔离

知识记录按以下字段做隔离：

- `user_id`
- `project_id`

这两个字段会在入库时写入 SQLite 元数据，也会作为 Milvus 检索过滤条件。

## 数据安全特征

- 项目工作流状态仅保存在内存里，降低了长期暴露面，但不具备持久性
- 原文文件会写入配置的 RAG 数据目录
- Milvus 不可用时，向量检索会自动退化
- OpenAI embedding 不可用时，会回退到确定性的哈希 embedding

## 已知缺口

- `user_id` 和 `project_id` 仍然由客户端直接传入，没有身份绑定
- 没有 authn / authz 层
- 没有限流或配额控制
- 没有审计日志链路
- 没有持久化的项目工作流存储

## 建议的下一步加固

1. 增加认证层，并从可信上下文推导 `user_id`。
2. 为 chat 和知识入库接口增加限流。
3. 为项目变更和知识写入增加审计日志。
4. 引入带访问控制边界的持久化项目存储。
