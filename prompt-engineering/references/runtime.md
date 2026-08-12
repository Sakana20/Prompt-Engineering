# 运行时兼容约定

## CLI

使用 `scripts/run_cli.py` 透明转发参数，不改写、不吞掉未知参数：

```bash
python scripts/run_cli.py -- compose --category 西瓜
python scripts/run_cli.py --debug -- validate-copy '口播正文'
python scripts/run_cli.py -- init-batch --task-name watermelon-batch --category 西瓜 --count 5 --task-prefix WM --output watermelon.tasks.json
python scripts/run_cli.py -- export-csv --input watermelon.tasks.json --config configs/projects/example.json
python scripts/run_cli.py -- validate-batch --input generated-task-batch.json --config configs/projects/example.json
python scripts/run_cli.py -- package --input generated-task-batch.json --format json --format csv --preset none
python scripts/run_cli.py -- learning-preflight --learning-root learning
python scripts/run_cli.py -- learning-transcribe --input /path/video.mp4 --learning-root learning --date 2026-08-11
python scripts/run_cli.py -- learning-transcribe --learning-root learning --date 2026-08-12
python scripts/run_cli.py -- learning-add-person-prompt --text "人物 Prompt" --source-label "用户人工样本" --learning-root learning
```

`AVATAR_PROMPT_PROJECT` 可覆盖项目根目录。`--project-root` 优先级更高。现有 CLI 参数完整
schema 见 [cli-parameters.schema.json](cli-parameters.schema.json)。默认使用 `uv run`；
`--python-executable` 或 `AVATAR_PROMPT_PYTHON` 可指定已经安装本项目的 Python 环境。

## 学习候选与发布

所有生产文案、人物 Prompt、任务清单和任务包流程在调用 `compose`、`init-batch`、
`validate-copy`、`validate-batch`、`package` 或 `export-csv` 前，必须先运行：

```bash
avatar-prompts learning-preflight --learning-root learning
```

该命令一次读取 copy/person 的 `approved` 与 `published` 候选，并核对 published 候选登记的
block ID 是否仍存在于正式 learned 资源。输出 `ready_for_generation`、`required_actions`、
完整 approved 候选、published 候选和正式 block ID。无阻塞项时退出码为 `0`；存在待发布候选
或正式资源缺失时退出码为 `3`，普通生成不得继续。

`codex_publish_approved` 只能由 Codex 处理：逐条清除样本价格、促销、平台、配送、品牌、功效、
销量、CTA、固定画面、logo 和真人风险，生成严格发布清单并执行 `learning-publish`。Python CLI
不得自动做语义抽取、自动批准或绕过发布清单。发布完所有 approved 候选后必须再次运行
`learning-preflight`；只有 `ready_for_generation=true` 且 `required_actions=[]` 才可继续原生产
命令。`repair_published_resources` 表示 published 候选登记的 block ID 不在正式资源中，必须先
恢复一致性，不能静默忽略。

`learning-transcribe` 传入 `--input` 时只处理显式本地文件或目录当前一层。省略 `--input` 时，
按本地日期（或 `--date`）解析用户指定的默认目录
`/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材`，仍然只扫描当前一层，不递归。
命令必须由用户或 Codex 明确运行；打开审核台不会自动转写。该命令只创建
`learning/copy/` 内容。
内容指纹与 worker 配置共同决定缓存；单项失败写入 copy failure report，不中断同批其他媒体。
默认 worker 使用 FunASR 既有 `.venv/bin/python -B` 执行 Prompt Engineering 自有
`funasr_worker.py`，主进程使用参数数组、`shell=False`、超时和严格 JSON 校验。FunASR 仓库
保持只读，现有字幕入口不参与此流程。

`learning-add-person-prompt` 的 `--text` 与 `--input` 互斥，只创建 `learning/person/` 候选，
不读取 copy 目录且不调用 ASR。`learning-list`、`learning-update`、
`learning-submit-review`、`learning-approve`、`learning-reject` 按 kind 操作独立候选；所有更新
必须携带 `expected_revision`，冲突不会覆盖新版本。原始识别稿和原始人物 Prompt 不可修改。

批准不等于发布。Codex 依据批准候选生成符合
[learning-publication.schema.json](learning-publication.schema.json) 的清单后，才可运行
`learning-publish`。CLI 校验 kind、candidate ID、revision、风险删除、强类型块和固定视觉
边界，并在全部目标通过后原子更新独立 learned resource；未批准、过期或部分失败均不发布。

本地审核台使用同一站点的“学习审核”工作台。视频文案页通过
`GET /api/learning/media?date=YYYY-MM-DD` 列出默认目录当前一层，用户多选后点击按钮才向
`POST /api/learning/transcribe` 提交 date 与服务器媒体 ID；左栏只保留日期和扫描控制，媒体
选择显示在中间主列表。静态资源禁用缓存，连接旧版服务时页面会提示重新运行审核台。客户端
不提交路径。勾选媒体后，右侧通过受限 `media-content` Range 接口预览最后勾选的视频或音频；
预览不会启动 ASR。真实转写使用清理继承变量后的 `-I -B` Python，并先预检 FunASR 模块；
失败响应只包含素材名和原因，页面保留失败选择用于重试，成功或复用时自动打开草稿。工作台还
提供新增人物 Prompt、保存和“提交学习”；“提交学习”是用户显式确认，会把已保存且分类完整的
`pending`/`editing` 候选直接转为 `approved`。兼容 CLI 仍保留提交审核、批准和驳回命令，但网页
不展示这层多人审核按钮。工作台不提供发布、导入、下游视频生成或付费提交按钮。
新候选原样保存 ASR 全文和 token 时间轴；初始可编辑稿只确定性移除中文逐字空格、保留 ASCII
词组内部单个空格并压缩相同重复标点，不补写标点、不纠错、不改变大小写。
文案详情中的品类族、消费需求和季节使用带中文说明的单选下拉；来源块用途使用“直接填槽”与
“AI 改写参考”复选项。提交学习前必须选择品类族、消费需求和至少一种用途并先保存。宽屏下三
个单选字段并排、两个来源用途并排，窄屏自动回到单列。未批准、未发布的
候选可携带 revision 移入 `learning/<kind>/trash/`；源素材不删除，媒体恢复“未识别”并可重新
转写为新候选。已批准或已发布候选禁止删除。

## 配置

Skill 输入配置使用 JSON、YAML 或 TOML 时，字段必须符合
[skill-config.schema.json](skill-config.schema.json)。未知字段不得静默丢弃。仓库原有
`pyproject.toml`、Prompt 资源和下游项目配置保持原样，不迁移、不删减。

Python CLI 当前支持一个项目一个 JSON 配置文件：

```bash
uv run avatar-prompts compose --config configs/projects/taobao-25-no-threshold-redpacket.json
uv run avatar-prompts validate-copy '口播正文' --config configs/projects/taobao-25-no-threshold-redpacket.json
```

项目配置文件代表一组完整且互斥的商品与活动口径。传入 `--config` 后，CLI 使用配置中的
`category`、商品事实、`platform`、`campaign_name`、`benefit_points`、
`campaign_forbidden_expressions`、`required_disclosures`、`confirmed_claims`、
`validation_config_path` 和 `language_style`；不得同时传入
`--benefit-point`、`--preset`、`--platform` 或 `--campaign-name`。如“淘宝闪购 12 元
无门槛红包”和“淘宝闪购 25 元无门槛红包”方向不同，应分别保存为两个项目配置，并在各自
配置中用 `campaign_forbidden_expressions` 禁止另一个口径。
兼容预设 `taobao-instant-commerce-default` 使用
`configs/projects/taobao-12-no-threshold-redpacket.json` 作为数据源。
`language_style` 只影响 Codex 的文案生成指令，不参与确定性校验；校验仍由活动契约、
禁词、行动引导和格式规则负责。
`validation_config_path` 指向独立校验配置，校验配置决定字数、禁词、行动引导禁用词和格式
前缀；不要在项目口径里维护 CTA 许可列表。
完整校验配置 schema 见 [validation-config.schema.json](validation-config.schema.json)。
`forbid_numeric_redpacket_amounts=true` 时，成稿不得出现阿拉伯数字或中文数字的红包金额；
该开关默认关闭，当前由 `configs/validation/taobao-compliance.json` 开启。
该合规校验配置与 25 元项目一样不设置行动引导禁用词，以便美食外卖投流口播在结尾使用自然引导语。
`confirmed_claims` 是确认可用但不强制每条都写入的活动事实或商品场景；不得从样本文案中
扩展出未确认品牌、价格、商品范围或配送承诺。

## 生成结果清单

Codex 完成语义生成后，将一对一结果写入符合
[generated-task-batch.schema.json](generated-task-batch.schema.json) 的 JSON。清单保留
`marked_script`、完整 `avatar_prompt`、`identity_key`、`outfit_key`、静态
`person_prompt`、`copy_mode`、`source_block_id`、`source_slot_values`、
`rewrite_anchor_phrases`，以及可选的 LibTV
`image_prompt` 和参考图字段。未提供 `image_prompt`
时复用 `person_prompt`。`notes` 不由输入清单指定，CLI 始终按真实品类和 1-based 序号生成。

`validate-batch` 校验逐条口播、两类静态画面 Prompt、批次文案相似度、50% 改写比例、
原文块来源与品类适配、商品插槽值、饮品饱腹逻辑、活动信息误入商品并列结构、
AI 改写保留字眼及人物/服装键唯一性。新清单的 `source_fill` 必须填写
`source_slot_values`；旧清单未提供该字段时仍可读。10 条必须包含 5 条
`human_rewrite` 和 5 条 `source_fill`/`natural_generate`；奇数批次的改写数为 `floor(N/2)`。
`natural_generate` 不登记任何真人来源字段。`package` 先执行同一套全批校验并检查所有目标文件均不存在，随后才按重复的
`--format` 参数写出产物。可选格式为 `json`、`markdown`、
`segmentation_manuscript`、`csv` 和 `libtv_omnihuman_package`。任何校验失败均不写文件。

Agent 不得自己编写 CSV 生成代码，也不得手工拼接 CSV 行。固定流程是：

```bash
uv run avatar-prompts init-batch \
  --task-name watermelon-batch \
  --category 西瓜 \
  --count 5 \
  --task-prefix WM \
  --output watermelon.tasks.json

# Agent 只填写 watermelon.tasks.json 中的空字段
uv run avatar-prompts export-csv \
  --input watermelon.tasks.json \
  --config configs/projects/taobao-12-no-threshold-redpacket.json
```

`export-csv` 固定调用仓库的 `write_oceanengine_csv(...)`。CSV 列顺序、标准库转义、
`NO_SPLIT` 标签移除、`notes={真实品类}+{序号}`、输出层级、UTF-8 原子写入和拒绝覆盖均由
项目代码负责；Agent 只能填写任务清单，不能复制或改写这些逻辑。

## 批处理

`count > 1` 或 `batch=true` 时执行批处理。每条记录保持独立的文案、人物、服装、
`identity_key`、`outfit_key`、`person_prompt`、`task_id` 和 notes。所有确定性校验必须
在写 CSV 前完成。

## 插件

当前 Python CLI 没有既有插件加载器。Skill 封装保留 Codex 已安装插件的调用能力，并用
`plugin_directories` 与 `plugins` 保存扩展声明。不得自动执行未知目录中的代码；只有用户
明确指定并且对应插件已安装、可调用时才使用。透明 CLI 转发保证未来底层增加插件参数后
无需修改封装器。

## 调试

`debug=true` 时输出：

- 解析后的非敏感配置；
- 执行阶段；
- 输入、输出文件路径；
- 校验问题；
- 转发命令。

不得输出 Cookie、Token、签名、验证码、浏览器 profile 内容或完整认证头。

## 输出

保留 `text`、`json`、`csv`、`markdown` 四种 Skill 输出，并增加独立的
`segmentation_manuscript` 交接格式：

- 每个任务写一份 `<task_id>.smartsplit.txt`，保留 `[[NO_SPLIT]]`；
- 每个批次写一份 Oceanengine CSV，`script` 写入前移除控制标签；
- JSON 保留结构化审计字段，Markdown 用于人工验证记录，text 用于单条直接结果。
- `libtv_omnihuman_package` 写出 LibTV CSV、interface JSON 和 plan Markdown 三件套。

统一输出层级为：

```text
/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/
├── <task_id>.smartsplit.txt
└── <task>.csv
```

日期使用本地 `YYYYMMDD`。同一任务的两类文件位于同一任务目录，但必须分别写入和记录；
写一种格式不得创建、覆盖或运行另一种格式。`target_project` 仅表示后续即创预检、导入
和执行目标，不是默认文件写出目录。

仓库内分别使用 `write_segmentation_manuscript(...)` 和 `write_oceanengine_csv(...)`。
两个 writer 都采用 UTF-8 原子写入并拒绝覆盖；调用方必须显式选择需要写出的产物。

## 开发后的 Codex 本地同步

每次修改生产代码、CLI、Prompt 模板、Schema 或本 Skill 后，都必须把当前工作区的
`prompt-engineering/` 同步安装到
`/Users/sakana/.codex/skills/prompt-engineering`。代码变更完成但本地 Skill 未同步时，任务
仍未完成。

同步前完成 Ruff、mypy 和完整 pytest；Skill 内容或结构变化时运行 `quick_validate.py`。
覆盖已安装目录前保留可恢复备份，且安装源必须是当前工作区，不能只依赖尚未包含本地修改
的远端分支。同步后执行：

```bash
diff -qr prompt-engineering /Users/sakana/.codex/skills/prompt-engineering
/usr/bin/python3 \
  /Users/sakana/.codex/skills/prompt-engineering/scripts/run_cli.py \
  --python-executable /Users/sakana/PyEnv/prompt-engineering/bin/python \
  -- --help
```

目录比对必须无差异，已安装 CLI 必须显示本次新增或修改的命令。最终回复同时报告工程测试、
Skill 校验、目录比对和 CLI 验证结果。
