# 通用商品口播规则

## 创作目标

围绕用户确认的商品与活动资料生成可直接口播的中文短视频文案。成稿应像真实用户分享一次
购买或使用决定：有一个与商品匹配的具体动机，商品事实清楚，利益点自然进入决定，每句话
提供新信息。表达顺序由当前商品、受众和传播目标决定，不使用固定开头、信息比例或结尾结构。

项目差异只由精简 `creative_brief` 提供：一个受众、一个传播目标、一句 voice 和最多三条
创意偏好。创意偏好用于指导选择，不产生确定性失败；事实、活动和合规要求仍由领域模型、
`ValidationConfig` 与验证器负责。

## 硬约束

- 只使用已确认商品与活动事实，不虚构材质、性能、价格、销量、品牌、功效、配送、促销或
  实时天气。
- 按 [campaign-contract.md](campaign-contract.md) 保留平台名、必填利益点、逐字口径、
  `NO_SPLIT` 片段、披露与活动禁用表达。
- 字符范围、明确禁词、行动引导禁用词、格式前缀和数字红包金额规则只取当前
  `ValidationConfig`。
- 最终只输出一段正文，不加标题、解释、Markdown、Emoji、编号或项目符号。
- 生成后使用与当前项目完全匹配的 `validate-copy`；失败时只根据本次命中的具体问题修改，
  不把整套规则重新追加给模型。

## 按模式动态生成

`compose` 默认使用 `natural_generate`，不读取或注入真人文案块。来源模式必须只选一个最终
采用块，并只注入当前模式的短合同：

- `natural_generate`：只使用商品、活动、时间、creative brief、成功标准和硬约束，自行选择
  最自然的生活切口；不登记来源字段。
- `human_rewrite`：只提供一个 `source_block_id`。借用其口语节奏，并至少保留两个确实出现于
  成稿的非季节性原字眼或短语；重写当前商品、需求和季节，不恢复样本活动事实。
- `source_fill`：只提供一个兼容块，只替换方括号，保留原词、原顺序、重复和停顿；商品段
  完整后再独立衔接当前活动。

`copy_mode`、`source_block_id`、`source_slot_values` 和 `rewrite_anchor_phrases` 的完整字段
合同保留在 Schema 与验证器，不重复塞进创作 Prompt。`source_fill` 和 `human_rewrite` 的选块、
品类、季节与字段规则见 [source-block-contracts.md](source-block-contracts.md)；正式来源正文见
[volume-copy-source-blocks.md](volume-copy-source-blocks.md)。

批次当前仍由任务清单和验证器保证 `human_rewrite=floor(N/2)`，其余条目优先兼容
`source_fill`、不足时使用 `natural_generate`。这属于批次策略与审计合同，不进入单条创作
Prompt；后续是否放宽应通过真实素材 A/B 盲评决定。

## 生成后检查

- 检查需求与商品、名词与动作、商品组成并列、结尾回指是否一致。
- 饮品必须使用饮用需求和“喝”的动作，不得保留食品饱腹逻辑。
- 当前季节按本地月份判断：3–5 月春季、6–8 月夏季、9–11 月秋季、12–2 月冬季。
  `source_fill` 不得使用跨季块；`human_rewrite` 可参考跨季块，但必须重建季节情境并只保留
  非季节性锚点。
- 平台、配送、红包、津贴、券、活动、链接和下单引导不得填入商品插槽或作为商品组成并列。
- 批量结果继续检查重复、高相似、来源重复和标签集中度；标签集中度属于人工复核预警。

## 双文件边界

每个任务输出一份
`/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task_id>.smartsplit.txt`
字幕稿，保留 `[[NO_SPLIT]]`。同一任务目录另输出 `<task>.csv`，`script` 只保留纯口播。
两类文件从同一份已校验结果派生，但独立写入、独立交接；生成一类文件不能自动创建、
覆盖、导入或运行另一类文件。日期使用本地 `YYYYMMDD`。
