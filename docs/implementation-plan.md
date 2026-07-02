# 实现计划

## 当前状态

### Phase 0：项目初始化（已完成）

- `taobao-avatar-video` Codex Skill 目录、`SKILL.md` 与 UI 元数据；
- 文案规则、数字人规则和即创 CSV 契约 references；
- `uv` Python 3.12+ 项目与 `src` 布局；
- 已验证文案 Prompt、数字人 Prompt 版本化资源；
- `ProductBrief`、`PromptPackage` 领域模型；
- Prompt 包编排、JSON 序列化与原子写入；
- `avatar-prompts compose` CLI；
- Ruff、mypy strict、pytest；
- 单元、集成和 CLI 端到端测试骨架；
- 可行性、架构、实现与开发文档。

### Phase 1：Skill 生成合约与本地校验（已完成）

- 已定义 `GeneratedScript`、`AvatarVideoPrompt`、验证问题和风险报告；
- 已校验 80–120 字、固定利益点、禁词、行动引导和单段正文格式；
- 已实现去空白字符计数，并明确其是字符规则而非真实口播时长；
- 已实现重复文案和二元字符 Jaccard 高相似检测；
- 已添加雨靴脱敏 golden case 和 CLI 端到端测试；
- 已提供 `avatar-prompts validate-copy` 确定性校验入口。

验收：Codex Skill 可根据代表性输入生成结果；无网络单元测试覆盖所有确定性规则；输出
不合规时明确失败，不静默修补关键事实。

### Phase 2：Skill 前向验证（进行中）

- 使用真实但脱敏的商品品类验证 Skill 触发与生成流程；
- 检查只输入品类和提供真实卖点两种模式；
- 检查单条及 5 条批量多样性；
- 记录规则版本、事实来源和生成时间；
- 根据失败样本迭代 `SKILL.md` 与 references。
- 已根据“防晒帽”失败样本将文案模板升级为 `2026-07-02-natural-v4`：取消固定五段式，
  改为单一生活片段、自然利益点衔接和 1–2 个具体使用动作；待用新样本继续前向验收。
- 已增加 SmartSplit `NO_SPLIT` 利益点标注；标签不计口播字数，并在数字人 Prompt 与
  Oceanengine CSV 边界移除。标注动作不触发 CSV 创建或导入。
- 已拆分为独立文件 writer：每任务字幕稿保留标签，每批次即创 CSV 移除标签；两类文件
  可分别生成且拒绝覆盖，不再由一个 Skill 调用另一个 Skill。

已完成样本：

- “西瓜”单品类草案：口播 111 字，规则校验通过；已生成数字人视频 Prompt 和静态
  `person_prompt`，未写入下游。详见
  [validation-watermelon.md](../tests/cases/validation-watermelon.md)。

验收：Codex 不依赖其他 LLM；事实不被扩写；失败不会产生下游 CSV。

### Phase 3：即创任务包

- 已用“西瓜”5 条样本验证完整 Prompt 到静态 `person_prompt` 的转换；
- 已生成兼容下游的 CSV；
- 已验证确定性任务 ID 和重复检测；
- 已调用下游 `preflight`，未自动 import；
- 保留 JSON 审计记录与 CSV 行映射。

验收：特殊字符、中文引号、逗号和换行均能通过下游预检。

### Phase 4：多人物差异与人工审核

- 确认每条人物身份键和服装键均唯一；
- 提供逐条文案、画面 Prompt、事实来源和风险预览；
- 记录批准人、批准时间和批准版本；
- 只有批准后的任务包可进入下游导入。

验收：批次内无重复人物或服装；未批准任务无法触发生产执行。

### Phase 5：受控下游接入

- 获得目标目录写权限；
- 安全写入 `input/`，不覆盖已有批次；
- 可选执行 `preflight` 和 `import`；
- 付费 `run-api-video` 永远保持单独显式确认；
- 先单条、后 5 条低频批次验收。

验收：任务归因 100%，中断恢复无重复提交，无凭据泄露。

### Phase 6：Skill 封装与安装（进行中）

- 保留 `compose`、`validate-copy` 及全部现有参数；
- 使用透明启动器转发当前与未来 CLI 参数；
- 为 CLI、启动器和 Skill 配置逐项提供 JSON Schema；
- 保留配置、批处理、Codex 插件声明、安全调试输出；
- 保留 text、JSON、CSV、Markdown 输出约定；
- 通过官方 Skill 校验后安装到 `$CODEX_HOME/skills/taobao-avatar-video`。

## 未决策项

1. 商品资料是否包含标题、详情文本、商品图或人工卖点；
2. 每次默认生成条数；
3. 完整视频 Prompt 是否还需由用户单独投递到即梦、可灵等视频模型。

## 文档同步规则

每完成一个阶段，立即更新本文件状态；接口变化更新 `architecture.md`；运行方式更新
`README.md`；风险结论变化更新 `feasibility-study.md`。
