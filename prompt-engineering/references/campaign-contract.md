# 活动利益点契约

- 每个任务支持 0–3 条用户确认的利益点。
- 每条利益点包含 `id`、`text`、`required`、`exact_match`、`no_split` 和 `priority`。
- `required=true` 时必须表达；`exact_match=true` 时逐字保留。
- `no_split=true` 时输出 `[[NO_SPLIT]]利益点原文[[/NO_SPLIT]]`。
- 无利益点时不得创造促销、金额、门槛或优惠。
- 多利益点按 `priority` 排序，并分别校验。
- 利益点中的禁词只在已确认原文范围内豁免。

兼容预设 `taobao-instant-commerce-default` 当前包含：
`淘宝闪购最高12元无门槛红包`。
