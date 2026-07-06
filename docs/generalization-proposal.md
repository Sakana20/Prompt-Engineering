# 通用化改造方案（确认稿）

状态：用户已确认，2026-07-03 已按本文方案完成首阶段实现。

## 1. 改造目标

将当前“淘宝闪购固定利益点数字人口播项目”改造成可复用的商品内容编排项目，使它能够：

- 接受不同品类和具体商品；
- 接受淘宝闪购不同活动利益点；
- 支持一个、多个或没有利益点的任务；
- 按任务选择文案规则、人物规则和输出目标；
- 保留 Codex 直接生成语义内容的模式，不接入其他 LLM 或模型 API；
- 保留现有字幕稿与即创 CSV 双文件输出；
- 保留现有淘宝闪购流程作为兼容预设，不让已经跑通的能力失效。

首阶段建议只泛化“商品 + 活动利益点 + 文案规则”，继续使用当前数字人规则和
Oceanengine CSV。其他平台和其他视频执行器只预留扩展接口，不在首阶段实现。

## 2. 改造前的耦合点

改造前实现有以下硬编码：

1. `ProductBrief` 只有商品资料，没有活动或利益点模型；
2. `REQUIRED_BENEFIT` 固定为“淘宝闪购最高12元无门槛红包”；
3. 校验器只认识这一条利益点，并为其中的“最”做专门禁词豁免；
4. 文案模板和 Skill reference 直接写入固定利益点；
5. `wrap_required_benefit()` 只能包装固定字符串；
6. Skill 名称、描述和规则都以淘宝闪购为唯一业务；
7. 输出契约默认只有 Oceanengine，虽然文件 writer 已经可以独立使用。

商品本身已经基本支持变化，主要缺口是活动规则仍然被当成代码常量。

## 3. 推荐的目标模型

### 3.1 商品资料 `ProductSpec`

```yaml
category: 哈密瓜
product_name: ""
selling_points: []
forbidden_claims: []
```

仅输入品类时仍属于草案模式，不得补充材质、性能、功效、价格、品牌或销量。

### 3.2 活动资料 `CampaignSpec`

```yaml
platform: 淘宝闪购
campaign_name: 日常红包活动
benefit_points:
  - id: primary-benefit
    text: 淘宝闪购最高12元无门槛红包
    required: true
    exact_match: true
    no_split: true
    priority: 1
forbidden_expressions: []
required_disclosures: []
```

`benefit_points` 建议支持 0–3 条。每条利益点独立声明：

| 字段 | 含义 |
|---|---|
| `id` | 稳定标识，用于校验报告和审计 |
| `text` | 用户确认的利益点原文 |
| `required` | 是否必须出现在文案中 |
| `exact_match` | 是否必须逐字保留 |
| `no_split` | 是否用 `[[NO_SPLIT]]…[[/NO_SPLIT]]` 包裹 |
| `priority` | 多利益点时的表达顺序 |

利益点只能来自用户输入或已确认预设，Codex 不得自行创造活动、金额、门槛或优惠。

### 3.3 文案规则 `CopyProfile`

```yaml
profile: product-led-conversational-v1
min_characters: 80
max_characters: 120
scene_ratio: 0.2
product_ratio: 0.5
benefit_and_purchase_ratio: 0.3
max_scene_sentences: 2
banned_expressions: []
calls_to_action: []
```

比例是 Codex 的语义指导，不做机械字符切割。确定性校验只负责可客观判断的规则：

- 字数；
- 必填利益点；
- 精确措辞；
- `NO_SPLIT` 标签完整性；
- 禁词和行动引导；
- 单段格式。

### 3.4 人物和输出规则

首阶段保留现有能力：

- `AvatarProfile`：年龄、人物风格、人物差异、服装差异、画面规则；
- `OutputProfile`：字幕稿、Oceanengine CSV、目录层级和字段映射；
- 输出目录继续使用
  `Prompt Engineering/<YYYYMMDD>/<task>/`。

后续如需其他视频执行器，再增加新的 `OutputProfile`，不修改商品或活动模型。

## 4. Prompt 组装方式

文案 Prompt 不再内置固定活动文案，而是按以下顺序组装：

```text
通用写作角色
  + 商品资料
  + 活动资料
  + 文案风格配置
  + 事实与合规边界
  + 输出格式要求
```

示意变量：

```text
{{PRODUCT_CONTEXT}}
{{CAMPAIGN_CONTEXT}}
{{COPY_PROFILE}}
{{COMPLIANCE_RULES}}
```

如果 `benefit_points` 为空，Prompt 不应强行生成促销内容；文案比例中的“利益点与购买体验”
退化为“购买或使用体验”。

## 5. 通用校验方案

建议将：

```python
validate_copy(text)
```

逐步升级为：

```python
validate_copy(text, contract)
```

`contract` 包含字数、利益点、禁词、行动引导和标签规则。校验流程为：

1. 解析并检查 `NO_SPLIT` 标签是否成对；
2. 去掉控制标签后统计口播字数；
3. 逐条检查必填利益点；
4. 对 `exact_match=true` 的利益点做逐字匹配；
5. 从禁词检查范围中仅移除已经匹配的合法利益点；
6. 检查其余禁词、行动引导和格式。

这样“最”等字符只在已确认利益点内部获得豁免，不再为某一条固定文案写特殊代码。

## 6. 双文件输出

每个任务仍输出两个互相独立的文件：

```text
Prompt Engineering/<YYYYMMDD>/<task>/
├── <task_id>.smartsplit.txt
└── <task>.csv
```

- 字幕稿保留所有 `no_split=true` 利益点的标签；
- CSV 的 `script` 去掉所有控制标签；
- 生成其中一种文件不触发另一种文件、预检、导入或付费生成；
- 其他输出目标以后通过 `OutputProfile` 增加，不把平台逻辑写进通用文案模型。

## 7. 预设与兼容方案

推荐保留一个现有业务预设：

```yaml
preset: taobao-instant-commerce-default
platform: 淘宝闪购
benefit_points:
  - text: 淘宝闪购最高12元无门槛红包
    required: true
    exact_match: true
    no_split: true
```

兼容策略：

- 旧入口未提供活动资料时，暂时加载该预设，保持现有行为；
- 新通用入口要求显式传入 `CampaignSpec` 或选择预设；
- 旧 CLI 参数全部保留，只新增参数，不删除或改义；
- 现有 golden cases 保留原预设标识和模板版本；
- 新增至少三组测试：替换利益点、多利益点、无利益点。

## 8. Skill 组织建议

最终采用“通用核心 + 单一通用化 Skill”：

```text
通用 Python 核心
├── 商品模型
├── 活动模型
├── 文案契约
├── 通用校验
└── 输出适配器

Codex Skills
└── prompt-engineering            # 通用商品数字人内容入口
```

Skill 不再拆分为两个包，避免在 Skill 内部形成互相引用或入口分裂。`prompt-engineering`
作为唯一入口，说明、规则和 schema 均按通用商品内容更新。用户指定
商品和利益点时使用用户利益点；用户只说淘宝闪购且未给利益点时加载淘宝默认预设。

## 9. 分阶段实施

### Phase A：领域模型与校验

- 增加 `CampaignSpec`、`BenefitPoint`、`CopyContract`；
- 将固定利益点改为配置输入；
- 实现通用标签、字数、利益点和禁词校验；
- 保留现有校验入口的兼容层。

### Phase B：Prompt 与预设

- 将文案模板改为变量化活动区块；
- 建立淘宝闪购兼容预设；
- 为替换利益点、多利益点、无利益点补充测试。

### Phase C：CLI 与 Schema

- 保留所有现有参数；
- 新增 `--preset`、`--campaign-file` 或等价配置入口；
- 为新增参数和配置字段更新 JSON Schema；
- JSON、YAML、TOML 配置继续使用同一领域模型。

### Phase D：通用 Skill

- 将当前 Skill 升级为 `prompt-engineering` 通用 Skill；
- 不新增第二个 skill 包；
- 更新 UI metadata、references 和触发描述；
- 对单一通用化 Skill 运行结构验证和真实品类前向验证。

### Phase E：输出适配器

- 保留 Oceanengine CSV；
- 只有出现明确的新下游需求时才新增适配器；
- 付费生成始终保持单独授权。

## 10. 建议的首轮验收用例

1. 当前淘宝闪购利益点：确保完全兼容；
2. 替换成另一条用户确认的淘宝闪购利益点：不改代码即可生成和校验；
3. 同一任务包含两条利益点：按优先级表达并分别校验；
4. 无利益点商品分享：不生成虚构促销；
5. 不同商品品类：食品、日用品、服饰各一组；
6. 字幕稿保留标签，CSV 去除标签；
7. 旧 CLI、批处理、插件、调试和输出格式全部回归通过。

## 11. 需要确认的决策

建议确认以下四项后再开始编码：

1. **首阶段范围**  
   推荐：先支持不同商品和不同淘宝闪购利益点；其他平台只预留接口。

2. **利益点数量**  
   推荐：支持 0–3 条，每条可配置是否必填、逐字保留和禁止拆分。

3. **兼容方式**  
   已调整：使用 `prompt-engineering` 作为唯一通用入口；不再新增第二个 skill。

4. **默认行为**  
   已调整：同一入口在用户给出利益点时使用用户利益点；用户只说淘宝闪购且未给利益点时
   默认当前利益点；用户明确无利益点时不生成促销口径。

确认以上决策后，再进入代码、Schema、测试、Skill 和文档的同步改造。
