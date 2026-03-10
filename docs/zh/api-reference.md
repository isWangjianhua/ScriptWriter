# API 参考

基础媒体类型：`application/json`

以下接口均为 project-scoped，且是当前实现中的真实接口。

## Project 数据结构

典型项目响应：

```json
{
  "project_id": "project_alpha",
  "title": "Pilot",
  "stage": "awaiting_confirmation",
  "current_artifact_type": "bible",
  "current_artifact_version_id": "bible_v1",
  "active_bible_version_id": "bible_v1",
  "active_outline_version_id": null,
  "active_draft_version_id": null
}
```

`stage` 可选值：

- `planning`
- `awaiting_confirmation`
- `drafting`
- `completed`
- `rewriting`

`current_artifact_type` 可选值：

- `bible`
- `outline`
- `draft`

## 项目接口

### `POST /api/projects`

请求体：

```json
{
  "project_id": "project_alpha",
  "title": "Pilot"
}
```

行为：

- 项目不存在时创建
- `project_id` 已存在时直接返回已有项目

响应：完整项目对象。

### `GET /api/projects/{project_id}`

返回当前项目对象。

错误：

- `404`：项目不存在

## Chat 工作流

### `POST /api/projects/{project_id}/chat`

请求体：

```json
{
  "message": "Write a crime thriller series",
  "title": "Pilot"
}
```

行为：

- 项目不存在时必须提供 `title`，接口会先创建项目
- 服务会把消息归类为：生成 bible、确认当前产物、生成 outline、继续 draft、重写 draft
- 响应是同步 JSON，不提供流式 NDJSON

常见流转：

- 新项目首次 chat -> 生成 `bible_v1`
- bible 待确认阶段批准 -> 生成 `outline_v1`
- outline 待确认阶段批准 -> 生成 `draft_v1`
- 继续写作 -> 生成下一个 draft 版本
- 重写请求 -> 生成新的 draft 版本

错误：

- `400`：项目不存在且未提供 `title`
- `404`：请求要求项目已存在，但项目不存在

响应：完整项目对象。

## 确认接口

### `POST /api/projects/{project_id}/confirm`

请求体：

```json
{
  "comment": "continue"
}
```

行为：

- 确认当前待审批产物
- 在适用时推动工作流进入下一个产物阶段

错误：

- `404`：项目不存在
- `400`：当前没有待确认产物

响应：完整项目对象。

## 知识上传

### `POST /api/projects/{project_id}/knowledge/upload`

请求体：

```json
{
  "user_id": "user_1",
  "content": "Reference notes for the project",
  "doc_type": "text",
  "title": "Story Guide",
  "path_l1": "season1",
  "path_l2": "episode1",
  "source_type": "reference",
  "version_id": "outline_v1",
  "episode_id": "ep1",
  "scene_id": "scene_2",
  "is_active": true
}
```

`doc_type` 可选值：

- `script`
- `novel`
- `text`
- `markdown`

响应：

```json
{
  "doc_id": "xxx",
  "chunk_count": 3,
  "source_path": "data/rag/sources/xxx.txt"
}
```

行为：

- 要求项目已存在
- 对 `content` 做分段和切块
- 默认把元数据写入 `data/rag/` 下的 SQLite
- Milvus 可用时写入向量索引

错误：

- `404`：项目不存在
- `400`：内容为空或 `doc_type` 非法

## 版本列表

### `GET /api/projects/{project_id}/versions`

响应：

```json
{
  "bible": [
    {
      "version_id": "bible_v1",
      "project_id": "project_alpha",
      "version_number": 1,
      "content": "...",
      "artifact_type": "bible",
      "status": "active"
    }
  ],
  "outline": [],
  "draft": []
}
```

错误：

- `404`：项目不存在

## 当前 API 不包含

- 不存在 thread-scoped 接口
- 不存在 run 恢复接口
- 不存在文件上传 / artifact 访问路由
- 不存在流式 chat 传输协议
