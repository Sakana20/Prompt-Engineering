# Prompt Engineering

Prompt Engineering 是商品短视频内容与数字人任务包项目。它负责把用户确认的商品事实、
活动口径和利益点整理成可审计的口播文案、数字人首帧 Prompt、SmartSplit 字幕稿、
Auto Oceanengine CSV，以及 LibTV OmniHuman 任务包。

本项目只做内容生成、确定性校验和文件交接；不登录平台、不提交付费生成、不导入即创任务。
Auto Oceanengine、LibTV 等下游执行器必须由用户另行确认后再运行。

## 当前能力

- 生成 80-100 字中文商品口播，支持通用商品、淘宝闪购默认利益点、无利益点任务，以及
  一个项目一个 JSON 配置文件的完整活动口径。
- 跑量批次固定 50% AI 贴近具体真人原文块改写；其余条目优先真人原文填槽，不兼容时使用
  `natural_generate`。奇数批次的改写数向下取整。AI 改写必须保留原文可辨认字眼与口语逻辑，不能退回规整的
  模板广告腔；原稿利益点仍不复用，成稿利益点只取当前任务配置。直填块还需通过品类
  与消费需求适配；兼容块不足时自动降级为无来源自然生成，不为凑比例强套。
- 生成 Prompt 自动注入当前本地日期、月份和季节；直接填槽轨过滤跨季原文块，AI 改写轨
  可借鉴跨季原文的非季节性字眼和口语逻辑，但必须把场景完整重建为当季版本。
  校验器仍拒绝成稿中的跨季表达，并拦截任务未确认的实时天气描述。
- 校验活动利益点、平台名、禁词、行动引导、`[[NO_SPLIT]]` 标签完整性、批量文案相似度及
  50% 改写比例、三模式字段边界和原文块来源去重；另外拦截饮品套用饱腹逻辑，以及平台、红包、
  津贴或配送被填入商品组成插槽。
- 支持“淘宝闪购合规”美食外卖项目配置：沿用 25 元项目的福利前置投流口径和行动引导，
  利益点改用大额红包、优惠价、活动价、福利价等模糊表达，并拦截阿拉伯和中文数字红包金额。
- 为每条口播生成静态数字人首帧 Prompt，并校验人物直视镜头、商品位于人物前方桌面、
  商品不由人物手持、人物不看商品不接触商品、非商品区域无 logo 和无字幕。
- 输出 SmartSplit 字幕稿：每个任务一份 `<task_id>.smartsplit.txt`，保留 `[[NO_SPLIT]]`。
- 输出 Auto Oceanengine CSV：每批次一份 `<task>.csv`，去除 `[[NO_SPLIT]]`，兼容参考图字段。
- 输出 LibTV OmniHuman 三件套：`<task>.libtv.csv`、`<task>.libtv.interface.json`、
  `<task>.libtv.plan.md`，只用于人审和后续执行，不创建画布或运行节点。
- 提供本地审核台，扫描 CSV 并可只读合并同目录 SQLite 中的任务状态。

## 输出边界

默认输出目录：

```text
/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/
```

常见任务包结构：

```text
<task>/
├── <task_id>.smartsplit.txt
├── <task>.csv
├── <task>.libtv.csv
├── <task>.libtv.interface.json
└── <task>.libtv.plan.md
```

这些产物彼此独立：写字幕稿不会自动写 CSV，写 CSV 不会导入 Auto Oceanengine，写 LibTV
任务包不会创建画布、创建节点或运行付费生成。

## Auto Oceanengine CSV

`write_oceanengine_csv(...)` 当前固定输出 10 列：

```csv
task_id,person_prompt,script,aspect_ratio,voice,title,notes,reference_image_uri,reference_image_url,reference_image_pid
```

字段说明：

| 字段 | 用途 |
|---|---|
| `task_id` | 唯一任务 ID，只含字母、数字、短横线和下划线 |
| `person_prompt` | 静态人物图 Prompt，供即创人物图片生成使用 |
| `script` | 纯口播文案，不含 `[[NO_SPLIT]]` |
| `aspect_ratio` | 默认 `9:16` |
| `voice` | 当前默认 `明朗女声` |
| `title` | 简短任务标题 |
| `notes` | `{品类}+{序号}`，例如 `西瓜+1` |
| `reference_image_uri` | 可选商品参考图素材 URI，常规稳定输入 |
| `reference_image_url` | 可选完整签名 URL；Auto Oceanengine 导入时会自动转成 URI 并重新签名 |
| `reference_image_pid` | 可选 PID，无值时留空 |

不提供参考图时，三个 `reference_image_*` 字段写空字符串，下游仍按默认文生图流程生成
数字人图片；提供 `reference_image_uri` 或仅提供完整 `reference_image_url` 时，下游会先
得到稳定 URI，再重新签名并把参考图传入人物图片生成请求的 `images[]`，用于约束商品外观。

## 项目配置

项目配置文件位于 `configs/projects/`，用于固化完整商品与活动口径。配置中可以声明：

- `category`、商品名和确认卖点；
- `platform` 和 `campaign_name`；
- 0-3 条 `benefit_points`；
- 互斥或禁用表达；
- 可提及但不强制出现的 `confirmed_claims`；
- `validation_config_path`；
- `language_style`。

传入 `--config` 后，CLI 使用配置文件作为完整口径，不再叠加默认淘宝闪购预设，也不要同时
传入 `--benefit-point`、`--preset`、`--platform` 或 `--campaign-name`。

`configs/projects/taobao-instant-commerce-compliance.json` 是无数字红包金额的美食外卖口径，
其品类、投流风格、配送场景和行动引导规则与 25 元项目一致，
引用 `configs/validation/taobao-compliance.json`。后者开启
`forbid_numeric_redpacket_amounts`，不影响现有 12 元和 25 元项目。

兼容预设：

- `taobao-instant-commerce-default`：从
  `configs/projects/taobao-12-no-threshold-redpacket.json` 读取，利益点为
  `最高12元无门槛红包`。
- `--preset none`：无利益点任务，不得自行创造促销、金额、门槛或平台权益。

## 常用命令

项目固定使用 Python 3.12+、`uv` 和 `/Users/sakana/PyEnv/prompt-engineering`：

```bash
export UV_PROJECT_ENVIRONMENT=/Users/sakana/PyEnv/prompt-engineering
uv sync --dev
```

生成基础文案/Prompt 包：

```bash
uv run avatar-prompts compose --category 雨靴 \
  --product-name 浅卡其色中筒雨靴 \
  --selling-point 浅卡其配色 \
  --selling-point 中筒款式
```

使用项目配置：

```bash
uv run avatar-prompts compose --config configs/projects/taobao-25-no-threshold-redpacket.json
uv run avatar-prompts compose --config configs/projects/taobao-instant-commerce-compliance.json
```

校验口播：

```bash
uv run avatar-prompts validate-copy '完整口播正文'
uv run avatar-prompts validate-copy '完整口播正文' \
  --config configs/projects/taobao-25-no-threshold-redpacket.json
```

Skill 透明入口：

```bash
python prompt-engineering/scripts/run_cli.py -- compose --category 西瓜
python prompt-engineering/scripts/run_cli.py --debug -- validate-copy '完整口播正文'
```

将 Codex 已生成的语义结果固化为任务产物：

```bash
uv run avatar-prompts init-batch \
  --task-name hami-melon-batch \
  --category 哈密瓜 \
  --count 5 \
  --task-prefix HM \
  --output hami-melon-batch.tasks.json

# Agent 只填写上面的 JSON，不编写 CSV 代码
uv run avatar-prompts export-csv \
  --input hami-melon-batch.tasks.json \
  --config configs/projects/taobao-12-no-threshold-redpacket.json

uv run avatar-prompts validate-batch \
  --input generated-task-batch.json \
  --config configs/projects/taobao-25-no-threshold-redpacket.json

uv run avatar-prompts package \
  --input generated-task-batch.json \
  --config configs/projects/taobao-25-no-threshold-redpacket.json \
  --format json \
  --format markdown \
  --format segmentation_manuscript \
  --format csv \
  --format libtv_omnihuman_package
```

输入清单格式见
[`prompt-engineering/references/generated-task-batch.schema.json`](prompt-engineering/references/generated-task-batch.schema.json)。
`package` 会先完成整批口播、首帧 Prompt、文案相似度、人物键和服装键校验，再检查全部
目标文件是否存在；任一步失败都不会开始写文件。CLI 不调用 LLM，文案与人物语义仍由
Codex 生成。输出只进入本项目日期/任务目录，不执行预检、导入或付费生成。

Oceanengine CSV 必须通过 `export-csv` 生成。Agent 不允许自行编写 CSV 序列化代码或手工
拼接行；字段顺序、引号与换行转义、`NO_SPLIT` 清理、`notes`、原子写入和拒绝覆盖均已
固化在项目 writer 中。

## 本地审核台

启动审核台：

```bash
uv run python tools/skill_reviewer/server.py
```

或运行前台脚本：

```bash
tools/skill_reviewer/run.sh
```

打开 `http://127.0.0.1:8765` 后，页面会优先扫描：

```text
/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材/Codex
```

列表只展示 CSV，并优先使用 `notes` 聚合命名。同目录中匹配到的 `.db`、`.sqlite` 或
`.sqlite3` 会作为只读状态来源，按 `task_id` 合并展示任务状态。Auto Oceanengine CSV 中的
`reference_image_*` 字段会在列表中显示“参考图/默认图”徽标，并在详情页展示参考图预览、
素材 URI、签名 URL 和 PID。审核台不写回 CSV、SQLite 或下游项目。

## 审核式学习

`avatar-prompts` 现在包含两套完全隔离的学习流程：

- `learning-transcribe`：只识别用户显式传入的本地媒体，调用 Prompt Engineering 自有
  worker，并使用 FunASR 既有环境；省略 `--input` 时按本地日期使用
  `/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材` 当前一层；不修改 FunASR，
  不进入现有字幕入口；
- `learning-add-person-prompt`：只在用户主动输入人物 Prompt 时创建人物候选，不调用 ASR；
- `learning-preflight`：汇总 approved/published 候选并核对正式块；六个生产 CLI 会在自身
  业务逻辑和文件写入前自动执行同一门禁，有待发布或资源不一致时以退出码 3 阻止继续；
- `learning-list/update/submit-review/approve/reject`：按 kind 与 revision 管理不可变原文、
  编辑稿和审计记录；
- `learning-publish`：只接收 Codex 为已批准候选生成的合法清单；文案块全有或全无地追加到
  原有 `volume-copy-source-blocks.md`，并保持原来的“块标题 + `text` 文案”格式；JSON 清单和
  审计字段不进入正式文案库，人物块继续写入独立人物资源。

默认运行根位于仓库 `learning/`（已忽略版本控制）。同一审核台顶部可切换“任务审核”和
“学习审核”；任务审核继续只读，学习审核只保留“保存修改”和“提交学习”两个主操作；提交学习
是用户的显式确认，会把已保存候选直接转为 `approved`，但仍不提供发布、下游导入、视频生成
或付费提交按钮。兼容 CLI 继续保留多人审核状态命令。视频文案页按日期从每日素材根目录开始，
逐层列出文件夹和当前层媒体；可以进入文件夹、返回上一层，并多选当前层媒体后点击“创建 ASR
候选”。日期和扫描控制保留在左栏，文件夹与多选操作显示在中间主列表，只转写已选媒体。
勾选媒体后，右侧详情区立即使用浏览器原生播放器预览最后勾选的视频或音频；预览支持 Range
请求和进度拖动，只读取服务端重新校验过的 date + directory ID + media ID，不接收浏览器文件路径。
点击“创建 ASR 候选”后，worker 以隔离 Python 参数运行并先预检 `funasr_timeline` 导入；逐条
失败会在左栏显示素材名和后端原因，失败项保持勾选以便修复后重试。成功或缓存复用的候选会
立即进入“学习候选”，右侧切换为待核对草稿。
候选的不可变原文与逐字时间轴保持 ASR 原样；初始可编辑稿只确定性移除中文逐字空格并压缩
明显重复标点，保留 ASCII 词组内部空格，不自动改字或猜测缺失标点。
品类族、消费需求和季节使用中文下拉选项，来源块用途使用可多选的“直接填槽 / AI 改写参考”；
必填分类未完成时不能提交学习。宽屏下三个单选分类并排、两个来源用途并排，窄屏自动改回单列。
分类控件的当前值和来源用途名称与可编辑稿使用相同正文尺寸，字段名和辅助说明保持小号。
草稿候选可按 revision 移入回收目录，删除后源视频仍在并恢复
为“未识别”，可重新创建新的 ASR 候选；已批准或已发布候选不能删除。候选状态徽标后的问号
会悬浮解释 pending/editing、ready_for_review、approved 和 published 是否已经可用于生成；列表行
的删除入口与候选内容共用同一选中底色，详情操作区则把保存/提交与删除按钮分组对齐。

学习审核的实际操作顺序如下：

1. 选择日期并扫描当天目录；需要时进入子文件夹或返回上一层，勾选一个媒体后，右侧只做视频
   或音频预览。
2. 点击“创建 ASR 候选”，成功后在中间“学习候选”列表打开待核对草稿。
3. 人工核对可编辑稿并补写必要标点、纠正错字；保存只更新编辑稿和 revision，不覆盖 ASR 原文。
4. 从中文控件选择品类族、消费需求、季节限制和至少一个来源块用途，保存后点击“提交学习”；
   候选直接进入 `approved`，等待 Codex 发布。
5. 对不满意且尚未批准/发布的候选点击“删除”；候选进入 `learning/<kind>/trash/`，源媒体不动。
6. 删除完成后，该媒体重新显示“未识别”，可再次勾选并创建一个全新候选。
7. 下一次运行任一生产 CLI 时，命令会自动执行 `learning-preflight`；若报告
   `codex_publish_approved`，CLI 在读写业务文件前停止，并把完整 approved 候选返回给 Codex。
8. Codex 逐条清除不可复用事实与风险、生成发布清单并执行 `learning-publish`；Python 不自动
   做语义清洗或批准。
9. Codex 再次运行 `learning-preflight`；只有退出码 0、`ready_for_generation=true` 且
   `required_actions=[]` 时才重试并继续原生产命令。直接在普通终端运行时也不能绕过该门禁，
   只会收到需要交由 Codex 处理的退出码 3 和 JSON 上下文。

例如，ASR 原文为：

```text
以 前 上 班 我 忍 气 吞 声 现 在 我 直 接 黑 化
```

初始可编辑稿是 `以前上班我忍气吞声现在我直接黑化`，而不是自动变成带标点的润色稿。
如果 ASR 原文已经带有标点，清洗器会保留；如果原文没有标点，则由审核人按视频语义补写。
这一边界避免自动断句改变原意，并保证不可变证据、机器初始化稿和人工修订稿可以分别追溯。

受控选项由后端统一提供：品类族为“饮品 / 非饮品”；消费需求包含“正餐、解馋、下午茶、
通勤、分享、追剧、日常使用、临时急需、送礼、其他”；季节限制为“全季通用 / 春季 / 夏季 /
秋季 / 冬季”；来源块用途可多选“直接填槽”和“AI 改写参考”。页面不会要求用户填写内部
机器值，服务端也拒绝列表之外的自由文本。

静态页面禁用浏览器缓存；若页面连接到更新前启动的服务，会明确提示重新运行
`tools/skill_reviewer/run.sh`。打开、扫描或刷新网页不会自动启动 ASR。

真实 Paraformer smoke test 需要用户提供短媒体样本；默认测试使用可注入 fake worker，不加载
模型。

## Skill 分发

可分发 skill 位于：

```text
prompt-engineering/
```

它包含：

- `SKILL.md`：触发条件、执行流程和安全边界；
- `references/`：文案规则、活动契约、数字人规则、运行时约定和 Oceanengine 契约；
- `scripts/run_cli.py`：透明转发 CLI 参数；
- JSON Schema：CLI 参数和 skill 配置；
- 生成结果 JSON Schema：Codex 到确定性 CLI 的交接契约；
- `agents/openai.yaml`：Codex UI 元数据。

已安装 skill 位于：

```text
/Users/sakana/.codex/skills/prompt-engineering
```

修改 `prompt-engineering/` 分发目录后运行：

```bash
uv run python /Users/sakana/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  prompt-engineering
```

## 质量检查

提交前运行：

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

## 文档

- [架构设计](docs/architecture.md)
- [实现计划](docs/implementation-plan.md)
- [开发规范](docs/development.md)
- [可行性研究](docs/feasibility-study.md)
- [LibTV OmniHuman 任务包设计笔记](docs/libtv-omnihuman-workflow-notes.md)
- [“西瓜”品类前向验证](tests/cases/validation-watermelon.md)

## 安全原则

- Codex 负责语义生成；Python 只做确定性编排、校验、序列化和文件写入。
- 人工样本只通过已审核的真人原文块进入生产 Prompt，不作为商品事实或利益点来源；模型
  只能填槽和按要求插入当前利益点，所有成稿仍须通过匹配当前活动的校验器。
- 不接入其他 LLM 或模型 API。
- 不虚构商品材质、性能、价格、销量、品牌、功效或促销。
- 不保存 Cookie、Token、验证码、签名、浏览器 profile 或真实业务凭据。
- 暂存 CSV、预检、导入、付费生成是四个独立授权边界。
