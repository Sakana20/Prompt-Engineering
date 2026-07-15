# 活动利益点契约

- 每个任务支持 0–3 条用户确认的利益点。
- 配置了 `platform` 时，每条口播必须逐字出现平台名；淘宝闪购项目不得省略“淘宝闪购”。
- 每条利益点包含 `id`、`text`、`required`、`exact_match`、`no_split` 和 `priority`。
- `required=true` 时必须表达；`exact_match=true` 时逐字保留。
- `no_split=true` 时输出 `[[NO_SPLIT]]利益点原文[[/NO_SPLIT]]`。
- 当多个利益点和固定衔接词必须作为连续字幕片段时，在项目配置中使用
  `no_split_phrases` 声明完整片段，例如
  `[[NO_SPLIT]]最高25元无门槛红包，还可以叠加九折津贴卡[[/NO_SPLIT]]`。
- 无利益点时不得创造促销、金额、门槛或优惠。
- 多利益点按 `priority` 排序，并分别校验；组合保护片段另行校验完整包裹。
- 利益点中的禁词只在已确认原文范围内豁免。
- 一个项目配置文件代表一个完整项目口径。方向不同或互相冲突的利益点不得混在同一任务中；
  应拆成不同项目配置，并用 `campaign_forbidden_expressions` 禁止串入口径。

兼容预设 `taobao-instant-commerce-default` 当前包含：
`最高12元无门槛红包`。
该预设从 `configs/projects/taobao-12-no-threshold-redpacket.json` 读取，避免代码与项目配置
维护两份 12 元口径。
