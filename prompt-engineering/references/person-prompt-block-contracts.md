# 人物 Prompt 学习块合约

- learned 块只补充 identity、hair、outfit、scene 四类可学习变量。
- 固定中景、直视镜头、商品前置摆放、不手持、不看不接触商品、非商品区域无 logo 和无字幕
  始终由生产模板与 validator 提供。
- 禁止具体真人复刻、未成年人、中老年、暴露、大面积 logo、夸张或土味方向。
- 同批 `identity_key` 与 `outfit_key` 继续保持唯一，learned 块不能取消现有校验。
- identity、hair、outfit 与 scene 块可独立重组；`incompatible_with` 中声明的组合不得使用。
