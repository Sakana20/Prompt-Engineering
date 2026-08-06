# 真人原文块语义合约

选块顺序固定为：区分品牌与商品 → 判断品类和消费需求 → 过滤兼容块 →
检查已确认商品资料能否填满插槽。不得先选块再强行套入商品。

## 直接填槽适配

- `learn-001-combination`：食品和饮品均可候选，但必须有主商品及至少两项已确认
  套餐组成、搭配、小料或配菜。“加、再加、外加、都给你配好了”中的对象
  必须全是商品内容。
- `learn-002-eating-order`、`learn-003-watch-snack`、`learn-004-afternoon`、
  `learn-005-not-hungry`、`learn-006-winter`、`learn-007-no-trouble`、
  `learn-008-evening`、`learn-012-squid-rhythm`、`learn-013-friends-at-home`、
  `learn-014-wrapped`、`learn-015-finally`、`learn-016-smell-texture`：当前原句
  都包含吃、饱腹或固体食品动作，只允许固体食品、正餐、快餐或零食直接填槽。
- 咖啡、奶茶、果茶、茶饮、果汁、豆浆、酸奶、可乐等饮品不得直接使用上述固体
  食品块。尤其不得将 `learn-005-not-hungry` 用于饮品。

## AI 改写适配

`human_rewrite` 可以参考不同品类原文块，但只保留非品类性字眼和说话逻辑。
饮品必须回到真实的饮用需求和“喝”的动作，不得保留“你不饿”“你就是饿了”
“人是铁饭是钢”“一顿不吃”等饱腹逻辑。商品名、使用动作、消费需求和结尾回指必须
指向同一件商品。

## 强类型插槽

- `source_fill` 必须在任务清单的 `source_slot_values` 中按原文顺序登记实际填入
  方括号的值。新清单留空将校验失败。
- 只能登记当前资料已确认的商品名、主商品、套餐组成、搭配、小料、配菜、
  温度状态、口感或食用动作。
- 平台、配送到家、红包、津贴、券、活动、链接和下单引导属于活动层，禁止进入
  `source_slot_values`，也禁止作为“加、再加、外加、配好了”的并列对象。
- 先完成原文块商品段，再用独立句子衔接当前活动信息。

## 比例与降级条件

`human_rewrite` 始终占 `floor(N/2)`；其余条目优先使用兼容且不重复的 `source_fill`。
兼容块或已确认商品资料不足时，剩余条目使用 `natural_generate`，不阻断整批生成。
`natural_generate` 不登记 `source_block_id`、`source_slot_values` 或
`rewrite_anchor_phrases`，不声称使用了真人原文。
