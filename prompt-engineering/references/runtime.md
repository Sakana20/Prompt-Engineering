# 运行时兼容约定

## CLI

使用 `scripts/run_cli.py` 透明转发参数，不改写、不吞掉未知参数：

```bash
python scripts/run_cli.py -- compose --category 西瓜
python scripts/run_cli.py --debug -- validate-copy '口播正文'
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
`campaign_forbidden_expressions` 和 `required_disclosures`；不得同时传入
`--benefit-point`、`--preset`、`--platform` 或 `--campaign-name`。如“淘宝闪购 12 元
无门槛红包”和“淘宝闪购 25 元无门槛红包”方向不同，应分别保存为两个项目配置，并在各自
配置中用 `campaign_forbidden_expressions` 禁止另一个口径。

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
