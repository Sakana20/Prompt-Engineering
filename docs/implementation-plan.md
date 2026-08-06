# 实现计划

## 当前状态

### Phase 11：真人原文块语义适配（已完成）

- 新增 `docs/source-block-semantic-design.md`，先固化品类适配、强类型插槽、活动隔离和停止条件；
- 新增原文块合约，饮品直接排除带吃、饱腹或固体食品动作的原文块；
- 新清单的 `source_fill` 登记 `source_slot_values`，CLI 校验插槽值命中及活动信息污染；
- 新增 `SOURCE_BLOCK_INCOMPATIBLE`、`INVALID_SOURCE_BINDINGS`、
  `CAMPAIGN_IN_PRODUCT_SLOT` 和 `PRODUCT_LOGIC_MISMATCH` 确定性问题码；
- 饮品无论轨道均拒绝“你不饿”“人是铁饭是钢”“一顿不吃”等饱腹逻辑；
- 组合原文块拒绝把平台、配送、红包、津贴、券、链接或下单引导写入商品并列结构；
- 改为三模式自适应分配：`human_rewrite` 固定占 `floor(N/2)`，其余条目优先
  `source_fill`，兼容块或商品资料不足时使用无来源 `natural_generate`，不再阻断饮品批次。

验收：瑞幸咖啡不能再直接使用“不饿”原文块；蜜雪冰城等饮品不能把配送、平台、红包或
津贴写成“加、再加、外加、配好了”的商品组成。

### Phase 10：真人跑量原文块固化与利益点隔离（已完成）

- 从 `docs/learn.txt` 直接保留审核通过的真人原句、句序、重复和口语停顿，不再提炼文风；
- 新增 `volume-copy-source-blocks.md`，商品事实位置替换为待填插槽，利益点相关行直接删除；
- 批次采用 `source_fill` 与 `human_rewrite` 双轨，10 条严格各 5 条，奇数批次的改写数向下
  取整；直接填槽轨保留完整原文块，AI 改写轨贴近一个具体原文块的字眼和口语逻辑；
- 任务清单记录 `copy_mode`、`source_block_id` 与 AI 改写实际保留的
  `rewrite_anchor_phrases`，CLI 校验比例、字段完整性、字眼命中和同轨来源去重；
- Prompt 禁止复用样本中的金额、价格、红包、券、活动、平台权益、配送、赠品和行动引导；
- 利益点只能来自当前任务配置或用户当次确认资料，无利益点任务保持 `--preset none`；
- 样本启发的候选文案仍必须通过匹配当前活动的 `validate-copy`，批量任务还需通过整批校验；
- 校验器新增 `UNCONFIRMED_PROMOTION`，拦截未被当前活动确认的起步价或低价利益点；
- Prompt 自动注入当前本地日期、月份和季节；校验器新增 `SEASON_MISMATCH` 与
  `UNCONFIRMED_CURRENT_WEATHER`，拒绝跨季节表达和未经确认的实时天气；
- 直接填槽轨过滤跨季原文块；AI 改写轨允许参考跨季块，但只保留非季节性原字眼，
  完整重建当季情境并继续通过 `SEASON_MISMATCH` 成稿校验；
- 增加回归测试，保证规则与 Prompt 不嵌入样本中的具体利益点。

验收：模板直接包含真人原文块、50% 双轨规则、贴近原字眼的改写约束、样本利益点隔离和
强制校验指令；已知样本利益点不会进入分发 Skill 或生成 Prompt。

### Phase 9：Skill 确定性工作流 CLI 固化（已完成）

- 保留 `compose` 与 `validate-copy` 的全部原有行为；
- 新增严格的生成结果清单 schema，保留文案、完整数字人 Prompt、静态 Prompt、人物键、
  服装键和下游字段的一对一映射；
- 新增 `validate-batch`，统一校验逐条内容、画面 Prompt、批次文案差异和人物/服装差异；
- 新增 `package`，支持审计 JSON、审核 Markdown、SmartSplit、Oceanengine CSV 和 LibTV
  三件套的显式按需输出；
- 输出前先完成全批校验与全路径覆盖检查，失败不开始写入；
- CLI 不调用其他 LLM，不预检、不导入、不创建画布、不提交付费生成。
- 新增 `init-batch` 与 `export-csv`，把 Agent 职责收窄为填写声明式 JSON；CSV 生成代码、
  字段、转义、标签清理、notes 和原子落盘全部固化在项目中。

验收：CLI 端到端测试证明选中的格式会独立落盘，未选择的格式不会创建，输出状态明确
`paid_generation_submitted=false`。

### Phase 8：LibTV OmniHuman 输出适配器（进行中）

- 新增 `libtv_omnihuman_package` 输出模式；
- 保持现有 Oceanengine CSV、SmartSplit 字幕稿和默认 `compose` 行为不变；
- 新增三件套产物：
  - `<task>.libtv.csv`：只保存逐条任务数据；
  - `<task>.libtv.interface.json`：保存 LibTV 接口、模型、节点、参数、命名、音色默认值和验收配置；
  - `<task>.libtv.plan.md`：保存人审计划；
- 首版不创建 LibTV 画布、不创建节点、不运行 `libtv node --run`，付费生成仍需用户单独确认；
- 默认语义音色：女声 `温暖闺蜜`，男声 `温润男声`；
- 默认音频约束：语速 `speed=1.2`，音量 `volume=8`（LibTV 音频节点字段为 `vol`）；
- 目标验收分辨率为 `720x1280`，作为产物验收目标而非 OmniHuman 可直接写入参数。

验收：LibTV 三件套 writer 可独立调用、拒绝覆盖、CSV 去除 `NO_SPLIT` 标签、interface JSON 明确执行边界。

### Phase 7：商品与活动通用化（已完成）

- 增加 `CampaignSpec`、`BenefitPoint` 和通用活动上下文；
- 支持 0–3 条利益点、替换利益点、多利益点和无利益点；
- 校验器按活动契约检查精确措辞、标签和禁词豁免；
- CLI 新增 `--preset`、`--platform`、`--campaign-name`、`--benefit-point`；
- CLI 新增 `--config` 项目配置入口，支持一个项目一个 JSON 配置文件；传入后使用配置中的
  商品和活动口径，不叠加默认预设或其他活动参数；
- 项目配置新增 `language_style`，用于按项目注入文案语气、叙述视角、句式节奏、表达重点
  和避免套话；
- 将 `prompt-engineering` 升级为通用化 Skill，并保留当前淘宝默认利益点兼容行为；
- 双文件和 Oceanengine 输出边界保持不变。

### Phase 0：项目初始化（已完成）

- `prompt-engineering` Codex Skill 目录、`SKILL.md` 与 UI 元数据；
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
- 已校验 80–100 字、活动利益点、禁词、行动引导和单段正文格式；
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
- 已根据前向反馈将文案模板升级为商品导向结构：场景约占 20%，商品和
  选择理由约占 50%，利益点与具体购买体验约占 30%，避免模板广告腔和过度生活叙事；
  待用新样本继续前向验收。
- 已增加 SmartSplit `NO_SPLIT` 利益点标注；标签不计口播字数，并在数字人 Prompt 与
  Oceanengine CSV 边界移除。标注动作不触发 CSV 创建或导入。
- 已拆分为独立文件 writer：每任务字幕稿保留标签，每批次即创 CSV 移除标签；两类文件
  可分别生成且拒绝覆盖，不再由一个 Skill 调用另一个 Skill。
- 两类 writer 默认按 `Prompt Engineering/<YYYYMMDD>/<task>/` 输出；同一任务的字幕稿
  与 CSV 位于同一目录，但仍分别生成。项目输出不等于写入即创项目。

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

### Phase 6：Skill 封装与安装（已完成）

- 保留 `compose`、`validate-copy` 及全部现有参数；
- 使用透明启动器转发当前与未来 CLI 参数；
- 为 CLI、启动器和 Skill 配置逐项提供 JSON Schema；
- 保留配置、批处理、Codex 插件声明、安全调试输出；
- 保留 text、JSON、CSV、Markdown、segmentation_manuscript 输出约定；
- 通过官方 Skill 校验后安装到 `$CODEX_HOME/skills/prompt-engineering`。

## 未决策项

1. 商品资料是否包含标题、详情文本、商品图或人工卖点；
2. 每次默认生成条数；
3. 完整视频 Prompt 是否还需由用户单独投递到即梦、可灵等视频模型。

## 文档同步规则

每完成一个阶段，立即更新本文件状态；接口变化更新 `architecture.md`；运行方式更新
`README.md`；风险结论变化更新 `feasibility-study.md`。
