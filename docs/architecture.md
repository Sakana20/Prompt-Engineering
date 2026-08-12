# 架构设计

## 目标

本项目提供通用商品内容核心和一个通用化 Codex Skill。Codex 将可信商品资料与活动资料转换为
可审计 Prompt 包，并可输出兼容 `Auto Oceanengine 26.6.22` 的任务 CSV。Codex 语义生成、
确定性校验、下游文件写入和付费视频执行保持分层。

## 组件

```text
ProductBrief
  → Codex 读取文案规则
  → Codex 生成 Script
  → 本地规则校验
  ├─ Segmentation Manuscript Writer
  │    → Prompt Engineering/<YYYYMMDD>/<task>/<task_id>.smartsplit.txt
  └─ Codex 读取数字人规则
       → Codex 生成 Avatar Video Prompt
       → 本地规则校验
       → Static Person Prompt Adapter
       → Oceanengine CSV Writer
       → Prompt Engineering/<YYYYMMDD>/<task>/<task>.csv
       → Human Approval
       → Auto Oceanengine
```

Codex 负责需要语义理解的判断和生成；Python 只处理适合确定性执行的校验、序列化和
CSV 文件操作，不调用另一个 LLM。

CLI 边界固定为两段：`compose` 生成供 Codex 使用的 Prompt 包；Codex 生成结果后写入
`generated-task-batch.schema.json` 定义的清单。`validate-batch` 只做整批确定性校验，
`package` 在同一校验通过后按需输出审计 JSON、审核 Markdown、SmartSplit、Oceanengine
CSV 或 LibTV 三件套。完整视频 Prompt 与身份/服装键保留在审计产物中，不因下游只消费
静态 Prompt 而丢失。

## 领域模型

`ProductBrief` 是所有生成的事实来源：

- `category`：必填品类；
- `product_name`：可选具体商品名；
- `selling_points`：用户确认过的真实卖点；
- `forbidden_claims`：不得生成的参数或表达。

仅提供品类时，`is_draft_only` 为真，所有输出必须人工复核。不能用模型生成内容反向充当
商品事实。

`CampaignSpec` 包含平台、活动名、0–3 条 `BenefitPoint`、活动禁用表达和必须披露内容。
每条利益点独立声明是否必填、是否逐字保留、是否用 `NO_SPLIT` 包裹及表达优先级。
默认淘宝预设只用于兼容旧的淘宝闪购使用方式；同一个 Skill 可替换利益点或明确选择无利益点。
“淘宝闪购合规”项目沿用 25 元项目的美食外卖品类、福利前置投流风格、配送场景和行动引导，
以“大额红包”为必填利益点，允许优惠价、活动价、福利价等无金额描述；它引用的
`ValidationConfig` 单独开启数字红包金额拦截，不改变其他项目。

`PromptPackage` 包含 schema 版本、模板版本、输入资料、文案 Prompt、数字人 Prompt 模板
和审核标记。JSON 是当前审计格式，后续可在不破坏领域层的情况下增加 SQLite。

`LanguageStyle` 描述项目级语言风格，包括语气、叙述视角、句式节奏、表达重点、避免套话
和额外风格规则。它从项目配置文件进入文案 Prompt，用于指导 Codex 生成；确定性校验不
判断风格好坏，只校验活动利益点、禁词、行动引导、标签和格式等客观规则。

`GeneratedScript` 与 `AvatarVideoPrompt` 表示 Codex 的两层生成结果。文案必须先通过
`CopyValidationReport`：字符数、活动契约、禁词、行动引导和格式均合格后，才进入
数字人 Prompt 阶段。批量结果另以二元字符 Jaccard 相似度检测重复和高同质内容；该指标
只做保守预警，不能替代 Codex 对场景和表达差异的语义判断。

## Skill 与 Prompt 资源

可分发 Skill 位于 `prompt-engineering/`。核心流程在 `SKILL.md`，详细规则按需放在
`references/`。`src/avatar_prompt_pipeline/templates/` 暂时保留完整基线模板，供开发期
回归和版本比较。每次模板或规则变更必须：

1. 更新 `TEMPLATE_VERSION`；
2. 更新模板快照或行为测试；
3. 在实现计划中记录变更；
4. 对代表性品类重新验收。

文案模板 `2026-08-06-adaptive-three-mode-v19` 定位为“商品导向的生活化分享”：场景或需求用
1–2 句话快速交代，约占 20%；商品、选择理由和 1–2 个已确认特点约占 50%；利益点与
具体购买体验约占 30%。场景只为商品服务，不展开成完整生活故事。确定性校验仍负责
字数、活动利益点、禁词、行动引导和单段格式，表达比例和自然度由 Codex 与人工审核判断。

跑量样本由 `volume-copy-source-blocks.md` 保存审核后的真人原句块。批次采用三模式：
`human_rewrite` 固定占 `floor(N/2)`；其余条目优先 `source_fill`，不兼容时使用
`natural_generate`。`source_fill` 保留原句原顺序并只填事实插槽；`human_rewrite` 参考一个具体
原文块，保留至少两个可辨认字眼或短语，并沿用反问、重复、短停顿和口语毛边进行改写。
`source_fill` 还要先通过 `source-block-contracts.md` 的品类和需求适配，并以
`source_slot_values` 审计实际填入的商品事实。10 条始终有 5 条改写与 5 条非改写；
同轨不重复 `source_block_id`。`natural_generate` 不登记来源字段，不伪装成真人原文。
样本中的金额、价格、券、红包、活动、平台
权益、配送、赠品、行动引导和商品断言不会进入事实层或活动层。生成结果仍必须使用当前 `CampaignSpec` 与
`ValidationConfig` 校验，未通过时不能进入数字人 Prompt 或任务导出。
校验器还会拒绝未被当前利益点或 `confirmed_claims` 覆盖的起步价表达，防止样本低价口径
从人工样本泄漏到生产文案。
Prompt 编排时按本地日期注入月份与季节，校验器采用 3–5 月春、6–8 月夏、9–11 月秋、
12–2 月冬的确定性规则拒绝成稿中的跨季节表达。`source_fill` 在选块阶段直接过滤
季节冲突块；`human_rewrite` 可把跨季块作为语言参考，但只保留非季节性锚点，并将
整个情境重建为当季版本，不允许机械替换季节词。实时雨雪、刮风、升降温等天气描述默认不可信，只有
被当前活动配置的 `confirmed_claims` 明确覆盖时才能通过。
任务清单通过 `copy_mode` 与 `source_block_id` 保存文案来源，直接填槽以
`source_slot_values` 保存商品插槽值，AI 改写另以
`rewrite_anchor_phrases` 登记至少两个实际保留的真人原文字眼；`validate-batch` 和 `package`
在落盘前校验改写比例、三模式字段边界、品类适配、插槽角色、饮品饱腹冲突、字眼命中及同轨来源去重。
旧清单没有 `source_slot_values` 时保持可读，新清单留空时不能通过。

生成态利益点使用 `[[NO_SPLIT]]…[[/NO_SPLIT]]` 标注，标签不计入口播字数。产物在此
扇出：同一任务目录位于 `Prompt Engineering/<YYYYMMDD>/<task>/`，其中字幕稿保留标签，
CSV 的 `script` 去掉标签。两类 writer 独立调用，任何一方都不能隐式触发、覆盖、导入
或运行另一方。

`prompt-engineering/` 是唯一分发 Skill。用户指定商品和利益点即可生成对应产物；用户只
给淘宝闪购场景且未指定利益点时，使用默认淘宝闪购利益点预设。

确定性 CLI 不承担自然语言创作。这样既能把 skill 的校验、去重、路径、拒绝覆盖和格式
适配固化成稳定命令，又不会绕过“Codex 是唯一语义生成器”的项目边界。

Oceanengine CSV 采用固定的“模板—填写—导出”接口。`init-batch` 创建声明式 JSON，Agent
只填写语义字段；`export-csv` 调用项目 writer 完成所有 CSV 结构与文件操作。Agent 不拥有
CSV 代码生成职责，因此不会在不同任务中重复实现或漂移字段契约。

对于方向不同或互相冲突的活动口径，使用“一个项目一个配置文件”。项目配置文件保存
`project_id`、商品资料、平台、活动名、利益点、活动禁用表达、披露要求、确认可用信息、
校验配置路径和语言风格；例如 12 元
无门槛红包项目与 25 元无门槛红包项目应拆成两个配置文件，分别禁止另一个利益点口径。
CLI 传入 `--config` 后只使用该配置中的商品与活动事实，不再叠加默认预设或其他活动参数。
行动引导禁用词和 `forbid_numeric_redpacket_amounts` 由独立校验配置维护，
项目配置只引用对应校验配置路径。

Skill 使用透明 CLI 启动器调用仓库入口，不复制或删减底层参数。CLI 与 Skill 配置分别由
`cli-parameters.schema.json`、`skill-config.schema.json` 描述。批处理、插件声明、安全
调试以及 text、JSON、CSV、Markdown、segmentation_manuscript 输出约定在 `runtime.md`
中；未知参数由启动器原样转发，避免封装层阻断底层未来能力。

## 执行边界

### Codex

Codex 是唯一语义生成器。Skill 必须向 Codex 提供事实边界、生成顺序、验证清单和下游
契约。不得规划供应商适配器、API Key、模型路由或重试其他 LLM。Codex 生成结果仍须经过
规则校验和人工审核，不能因生成完成就视为可投放。

### Auto Oceanengine

现有下游 CSV 字段是 `task_id`、`person_prompt`、`script`、`aspect_ratio`、`voice`、
`title`、`notes`、`reference_image_uri`、`reference_image_url`、`reference_image_pid`。
其 `person_prompt` 用于人物图片生成，不是完整视频 Prompt；参考图字段为空时保持默认
文生图流程，提供 `reference_image_uri` 时约束人物图生成中的商品外观。

写入下游前必须：

- 生成唯一且确定的 `task_id`；
- 通过下游 `preflight`；
- 不覆盖未知文件；
- 保留上游 Prompt 包与任务 ID 的映射；
- 在付费提交前人工确认。

### 本地审核台

`tools/skill_reviewer/` 提供一个只读人工审核界面。前端负责 CSV 解析、搜索、行详情展示、
自动高亮和 `localStorage` 配置保存；本地 Python 标准库服务承担静态文件托管、每日目录
扫描和 SQLite 状态读取。默认扫描
`/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材/Codex`，列表只展示 CSV，并用
`notes` 字段前缀聚合成人工可读批次名；匹配到同目录 SQLite 时，按 `task_id` 把
`jobs.status` 合并成行状态徽标。审核台不写回 CSV 或数据库，不调用 Auto Oceanengine，
不执行导入、生成或付费提交。

学习工作台显示独立的每日媒体默认目录
`/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材`。视频文案页通过受限 API 列出当前
一层媒体，浏览器只持有服务端签发的稳定 ID；用户点击按钮时，服务端重新扫描并验证 ID 后才
调用同一 `LearningService.transcribe(...)`。`learning-transcribe` 未提供 `--input` 时也按
本地日期解析该目录。两条入口共享领域服务与缓存，不影响任务 CSV 的 `/素材/Codex` 入口。

### LibTV OmniHuman

LibTV 是新增输出适配器，不替换 Auto Oceanengine。首版只生成可审阅任务包，不创建画布、
不创建节点、不运行 `libtv node --run`。

LibTV OmniHuman 任务包由三份文件组成：

```text
<task>.libtv.csv
<task>.libtv.interface.json
<task>.libtv.plan.md
```

- CSV 只保存逐条任务数据：`task_id`、`title`、`notes`、`image_prompt`、`audio_prompt`、
  `voice_label`、`voice_id`、`aspect_ratio`；
- interface JSON 保存接口类型、模型、节点模板、可写模型参数、默认音色、验收分辨率和
  执行边界；
- plan Markdown 供人工审阅。

默认语义音色为女声 `温暖闺蜜`、男声 `温润男声`。其中 `温暖闺蜜` 的 LibTV/TTS
`voice_id` 为 `Chinese (Mandarin)_Warm_Bestie`，`温润男声` 的 `voice_id` 为
`Chinese (Mandarin)_Gentleman`。默认音频约束为 `speed=1.2`、音量 `volume=8`，写入
LibTV 音频节点时音量使用 schema 字段 `vol`。目标成片规格为 `720x1280`，但这是验收目标，
不是 OmniHuman 1.5 当前可直接写入的 `resolution` 参数。

### 多人物与服装差异

每条 Prompt 必须生成不同中国女生与不同服装。语义生成阶段为每条结果同时提供
`identity_key` 和 `outfit_key`，确定性校验器负责检查批次内两组键都唯一。人物身份可通过
脸型、可见五官、发型、发色和长相方向区分；服装以完整搭配区分。不同人物仍保持
22–24 岁中国女生、年轻、自然、干净、生活化的统一账号审美。长相方向可覆盖甜美、可爱、
清冷、御姐、邻家和清爽等年轻主流审美，禁止大妈、阿姨、中年女性、中老年或老气方向。
服装覆盖通勤、休闲、甜酷、简约和轻运动等主流日常方向，避免暴露、土味、夸张和大面积
logo。静态人物图和 LibTV 首帧必须优先定义为数字人口播
首帧，而不是生活方式抓拍；人物说话时必须直视镜头并保持稳定镜头交流。场景只作为背景，
不得驱动人物做准备、收拾、换鞋、低头看桌面、看包或看商品等动作。商品不得由人物手持，
必须放在人物面前的桌面、餐桌、台面或办公桌上；不得放在人物身后、背景里、远处、侧后方、
沙发、玄关或购物袋中。人物不看商品、不接触商品，商品只能作为环境中的静态可见物出现。

## 审核式学习架构

学习域位于 `src/avatar_prompt_pipeline/learning/`。`copy` 与 `person` 共用安全 ID、原子写入、
revision 和审计事件基础设施，但拥有独立 dataclass、目录、schema、状态记录和正式资源。
原始 `raw_transcript`/`raw_prompt` 不可更新；所有可写操作都要求 `expected_revision`。

ASR 主进程通过参数数组和 `shell=False` 调用 Prompt Engineering 自有 `funasr_worker.py`。
worker 由 FunASR 既有 Python 使用 `-B` 执行，正常 import 已安装的 `funasr_timeline`，只把
转换音频与 JSON 写到 `learning/copy/work/`。FunASR 源码、锁文件、缓存与现有字幕入口保持
只读。内容指纹与 worker 配置共同缓存，单项失败落独立报告。

候选经工作台或 CLI 人工批准后仍不能自动进入生产。Codex 负责语义拆解并生成发布清单；
`learning-publish` 只做确定性校验、风险隔离、冲突检查和多目标事务写入。文案块发布到
`learned-copy-source-blocks.md` 并进入 source-block 注册表；人物 identity/hair/outfit/scene
块发布到独立资源并进入视觉 Prompt 指令，固定画面约束仍由原模板和 validator 提供。

审核台复用原站点外壳。任务工作台继续只读 CSV/SQLite；学习工作台使用专用受限 API，候选
操作只能提交 kind、candidate ID、revision 与允许字段；媒体操作只能提交 date 和扫描得到的
media ID。视频文案页在左栏选择日期，中间主列表展示当天媒体和学习候选。静态资源响应使用
`no-store`，避免新页面连接旧缓存脚本；旧服务缺少媒体 API 时前端给出重启提示。客户端不能
提交目标路径。勾选媒体时，右侧通过受限 `media-content` API 预览最后勾选项；该 API 每次按
date + media ID 重新发现并校验当前层文件，支持 HTTP Range，不返回路径。预览不能触发发布、
ASR、下游视频生成或付费提交。

转写 provider 清除继承的 Python 路径、虚拟环境和 macOS `__PYVENV_LAUNCHER__`，使用
`-I -B` 启动 FunASR 既有 Python，并在首次媒体前预检所需模块。预检失败仍按单项失败合约写报告；审核台
响应只返回素材名和错误，不返回源路径。前端保留失败项选择并展示逐项原因，成功项自动打开
新建或复用的候选草稿。
虚拟环境解释器路径只转为绝对路径，不得调用 `resolve()`；后者会解析 macOS `.venv/bin/python`
符号链接并退化为基础解释器，从而丢失 FunASR 环境的 `site-packages`。

## 安全与可恢复性

- JSON、字幕稿和 CSV 写入采用临时文件原子替换；
- API 凭据只从运行环境读取，不写入项目；
- 模型生成与视频提交分开授权；
- 所有生产输出保留模板版本、事实输入和审核状态；
- 外部写入失败不得触发视频提交或盲目重试。
