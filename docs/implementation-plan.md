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

### Phase 1：Skill 生成合约与本地校验（下一阶段）

- 定义 `GeneratedScript`、`AvatarVideoPrompt` 和风险报告；
- 校验 80–120 字、固定利益点、禁词与禁止行动引导；
- 区分字符数和中文口播时长；
- 建立多条文案的场景与表达差异检测；
- 对代表性商品建立脱敏 golden cases。

验收：Codex Skill 可根据代表性输入生成结果；无网络单元测试覆盖所有确定性规则；输出
不合规时明确失败，不静默修补关键事实。

### Phase 2：Skill 前向验证

- 使用真实但脱敏的商品品类验证 Skill 触发与生成流程；
- 检查只输入品类和提供真实卖点两种模式；
- 检查单条及 5 条批量多样性；
- 记录规则版本、事实来源和生成时间；
- 根据失败样本迭代 `SKILL.md` 与 references。

验收：Codex 不依赖其他 LLM；事实不被扩写；失败不会产生下游 CSV。

### Phase 3：即创任务包

- 将完整数字人视频 Prompt 转换为静态 `person_prompt`；
- 生成兼容下游的 CSV；
- 确定性任务 ID 和重复检测；
- 调用下游 `preflight`，但不自动 import；
- 保留 JSON 审计记录与 CSV 行映射。

验收：特殊字符、中文引号、逗号和换行均能通过下游预检。

### Phase 4：固定 IP 与人工审核

- 确认固定参考图或人物素材复用策略；
- 提供逐条文案、画面 Prompt、事实来源和风险预览；
- 记录批准人、批准时间和批准版本；
- 只有批准后的任务包可进入下游导入。

验收：人物身份策略经真实样本验证；未批准任务无法触发生产执行。

### Phase 5：受控下游接入

- 获得目标目录写权限；
- 安全写入 `input/`，不覆盖已有批次；
- 可选执行 `preflight` 和 `import`；
- 付费 `run-api-video` 永远保持单独显式确认；
- 先单条、后 5 条低频批次验收。

验收：任务归因 100%，中断恢复无重复提交，无凭据泄露。

## 未决策项

1. 商品资料是否包含标题、详情文本、商品图或人工卖点；
2. 固定 IP 是严格同脸还是风格一致；
3. 每次默认生成条数；
4. 完整视频 Prompt 是否还需由用户单独投递到即梦、可灵等视频模型。

## 文档同步规则

每完成一个阶段，立即更新本文件状态；接口变化更新 `architecture.md`；运行方式更新
`README.md`；风险结论变化更新 `feasibility-study.md`。
