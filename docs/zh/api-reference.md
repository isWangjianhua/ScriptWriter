# API 参考

基础媒体类型：

- JSON：`application/json`
- 聊天流：`application/x-ndjson`

以下接口均为 thread-scoped。

## Chat

### `POST /api/threads/{thread_id}/chat`

请求体：

```json
{
  "message": "Write a suspense opening scene",
  "user_id": "user_1",
  "project_id": "project_alpha",
  "resume_run_id": "optional_previous_run_id"
}
```

行为：

- 校验 `thread_id`
- 校验 `user_id` + `project_id`
- 可选基于 `resume_run_id` 做受限恢复
- 执行编排并以 NDJSON 输出事件

NDJSON 事件类型：

- `run_started`
- `canvas_update`
- `chat_chunk`
- `critic_note`
- `error`

## Run 恢复

### `GET /api/threads/{thread_id}/runs/{run_id}?user_id=...&project_id=...`

返回：

- run 元信息（`run_id`、`session_id`、`thread_id`、`status`）
- 恢复后的 `state`
- 全量 `events`
- 重放信息（`replay_from_seq`、`replayed_events`）

安全语义：

- `404`：run 不存在
- `403`：run 存在但 thread 或租户归属不匹配

## 知识入库

### `POST /api/threads/{thread_id}/knowledge/ingest`

请求体：

```json
{
  "user_id": "user_1",
  "project_id": "project_alpha",
  "doc_type": "script",
  "title": "Pilot",
  "path_l1": "season1",
  "path_l2": "ep1",
  "content": "INT. ROOM - DAY\nHe sits.",
  "doc_id": "optional_doc_id"
}
```

响应：

```json
{
  "doc_id": "xxx",
  "chunk_count": 12,
  "source_path": "..."
}
```

`doc_type` 可选：`script`、`novel`、`text`、`markdown`。

## 知识上传

### `POST /api/threads/{thread_id}/knowledge/upload`

表单字段：

- 必填：`file`、`user_id`、`project_id`
- 可选：`title`、`path_l1`、`path_l2`、`doc_type`

响应：

```json
{
  "doc_id": "xxx",
  "chunk_count": 3,
  "filename": "my_novel.txt",
  "title": "my_novel",
  "doc_type": "markdown",
  "virtual_path": "/mnt/user-data/uploads/my_novel.txt",
  "artifact_url": "/api/threads/thread_alpha/artifacts/mnt/user-data/uploads/my_novel.txt"
}
```

限制与错误：

- 文件上限由 `SCRIPTWRITER_MAX_UPLOAD_BYTES` 控制
- 超限返回 `413`
- 路径穿越会被拦截

### `GET /api/threads/{thread_id}/knowledge/upload/list`

返回线程上传文件列表。

### `DELETE /api/threads/{thread_id}/knowledge/upload/{filename}`

删除线程上传目录中的单个文件。

## Artifacts

### `GET /api/threads/{thread_id}/artifacts/{path}`

通过虚拟路径读取文件：

- `path` 必须以 `mnt/user-data/...` 开头
- 文本/HTML 支持 inline
- `?download=true` 可强制附件下载

示例路径：

- `mnt/user-data/uploads/my_novel.txt`
- `mnt/user-data/outputs/final_draft.md`

## 与旧接口的破坏性变更

- 删除 `POST /api/chat`
- 删除 `GET /api/runs/{run_id}`
- 删除所有非 thread-scoped 知识接口
- 删除 `default_user/default_project` 回退
