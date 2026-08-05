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
```

`AVATAR_PROMPT_PROJECT` 可覆盖项目根目录。`--project-root` 优先级更高。现有 CLI 参数完整
schema 见 [cli-parameters.schema.json](cli-parameters.schema.json)。默认使用 `uv run`；
`--python-executable` 或 `AVATAR_PROMPT_PYTHON` 可指定已经安装本项目的 Python 环境。

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

`validate-batch` 校验逐条口播、两类静态画面 Prompt、批次文案相似度、50% 双轨比例、
原文块来源与品类适配、商品插槽值、饮品饱腹逻辑、活动信息误入商品并列结构、
AI 改写保留字眼及人物/服装键唯一性。新清单的 `source_fill` 必须填写
`source_slot_values`；旧清单未提供该字段时仍可读。10 条必须包含 5 条 `source_fill` 和 5 条
`human_rewrite`；奇数批次的改写数为 `floor(N/2)`。`package` 先执行同一套全批校验并检查所有目标文件均不存在，随后才按重复的
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
