# 人物 Prompt 学习块合约

- learned 块只补充 identity、hair、outfit、scene 四类可学习变量。
- 固定中景、直视镜头、商品前置摆放、不手持、不看不接触商品、非商品区域无 logo 和无字幕
  始终由生产模板与 validator 提供。
- 禁止具体真人复刻、未成年人、中老年、暴露、大面积 logo、夸张或土味方向。
- 同批 `identity_key` 与 `outfit_key` 继续保持唯一，learned 块不能取消现有校验。
- identity、hair、outfit 与 scene 块可独立重组；`incompatible_with` 中声明的组合不得使用。
- 正式人物库使用 `### block-id · block-type` 加 fenced `text` 的可读格式，与正式文案块一致；
  来源候选、兼容标签、风险清理和发布清单只保存在本地 provenance 审计中。
- 正常生成只使用 `compose` 注入的限量选择：identity 2、hair 2、outfit 4、scene 2；不得把
  完整正式人物库加入 Prompt。当前季节与块正文冲突时必须排除该块。
