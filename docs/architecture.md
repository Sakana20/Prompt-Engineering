# 架构设计

## 目标

本项目是 Codex Skill。Codex 将可信商品资料转换成可审计的 Prompt 包，并最终输出兼容
`Auto Oceanengine 26.6.22` 的任务 CSV。Codex 语义生成、确定性校验、下游文件写入和
付费视频执行是四个清晰阶段。

## 组件

```text
ProductBrief
  → Codex 读取文案规则
  → Codex 生成 Script
  → 本地规则校验
  ├─ Segmentation Manuscript Writer
  │    → Prompt Engineering/<YYYYMMDD>/<task>/<task_id>.smartsplit.txt
  └─ Codex 读取数字人规则
       → Codex 生成 Avatar Video Prompt
       → 本地规则校验
       → Static Person Prompt Adapter
       → Oceanengine CSV Writer
       → Prompt Engineering/<YYYYMMDD>/<task>/<task>.csv
       → Human Approval
       → Auto Oceanengine
```

Codex 负责需要语义理解的判断和生成；Python 只处理适合确定性执行的校验、序列化和
CSV 文件操作，不调用另一个 LLM。

## 领域模型

`ProductBrief` 是所有生成的事实来源：

- `category`：必填品类；
- `product_name`：可选具体商品名；
- `selling_points`：用户确认过的真实卖点；
- `forbidden_claims`：不得生成的参数或表达。

仅提供品类时，`is_draft_only` 为真，所有输出必须人工复核。不能用模型生成内容反向充当
商品事实。

`PromptPackage` 包含 schema 版本、模板版本、输入资料、文案 Prompt、数字人 Prompt 模板
和审核标记。JSON 是当前审计格式，后续可在不破坏领域层的情况下增加 SQLite。

`GeneratedScript` 与 `AvatarVideoPrompt` 表示 Codex 的两层生成结果。文案必须先通过
`CopyValidationReport`：字符数、固定利益点、禁词、行动引导和格式均合格后，才进入
数字人 Prompt 阶段。批量结果另以二元字符 Jaccard 相似度检测重复和高同质内容；该指标
只做保守预警，不能替代 Codex 对场景和表达差异的语义判断。

## Skill 与 Prompt 资源

可分发 Skill 位于 `taobao-avatar-video/`。核心流程在 `SKILL.md`，详细规则按需放在
`references/`。`src/avatar_prompt_pipeline/templates/` 暂时保留完整基线模板，供开发期
回归和版本比较。每次模板或规则变更必须：

1. 更新 `TEMPLATE_VERSION`；
2. 更新模板快照或行为测试；
3. 在实现计划中记录变更；
4. 对代表性品类重新验收。

文案模板 `2026-07-02-product-led-v5` 定位为“商品导向的生活化分享”：场景或需求用
1–2 句话快速交代，约占 20%；商品、选择理由和 1–2 个已确认特点约占 50%；利益点与
具体购买体验约占 30%。场景只为商品服务，不展开成完整生活故事。确定性校验仍负责
字数、固定利益点、禁词、行动引导和单段格式，表达比例和自然度由 Codex 与人工审核判断。

生成态利益点使用 `[[NO_SPLIT]]…[[/NO_SPLIT]]` 标注，标签不计入口播字数。产物在此
扇出：同一任务目录位于 `Prompt Engineering/<YYYYMMDD>/<task>/`，其中字幕稿保留标签，
CSV 的 `script` 去掉标签。两类 writer 独立调用，任何一方都不能隐式触发、覆盖、导入
或运行另一方。

Skill 使用透明 CLI 启动器调用仓库入口，不复制或删减底层参数。CLI 与 Skill 配置分别由
`cli-parameters.schema.json`、`skill-config.schema.json` 描述。批处理、插件声明、安全
调试以及 text、JSON、CSV、Markdown、segmentation_manuscript 输出约定在 `runtime.md`
中；未知参数由启动器原样转发，避免封装层阻断底层未来能力。

## 执行边界

### Codex

Codex 是唯一语义生成器。Skill 必须向 Codex 提供事实边界、生成顺序、验证清单和下游
契约。不得规划供应商适配器、API Key、模型路由或重试其他 LLM。Codex 生成结果仍须经过
规则校验和人工审核，不能因生成完成就视为可投放。

### Auto Oceanengine

现有下游 CSV 字段是 `task_id`、`person_prompt`、`script`、`aspect_ratio`、`voice`、
`title`、`notes`。其 `person_prompt` 用于人物图片生成，不是完整视频 Prompt。

写入下游前必须：

- 生成唯一且确定的 `task_id`；
- 通过下游 `preflight`；
- 不覆盖未知文件；
- 保留上游 Prompt 包与任务 ID 的映射；
- 在付费提交前人工确认。

### 多人物与服装差异

每条 Prompt 必须生成不同人物与不同服装。语义生成阶段为每条结果同时提供
`identity_key` 和 `outfit_key`，确定性校验器负责检查批次内两组键都唯一。人物身份可通过
脸型、可见五官、发型和发色区分；服装以完整搭配区分。不同人物仍保持年轻、自然、干净、
生活化的统一账号审美。

## 安全与可恢复性

- JSON、字幕稿和 CSV 写入采用临时文件原子替换；
- API 凭据只从运行环境读取，不写入项目；
- 模型生成与视频提交分开授权；
- 所有生产输出保留模板版本、事实输入和审核状态；
- 外部写入失败不得触发视频提交或盲目重试。
