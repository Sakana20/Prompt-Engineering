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

保留 `text`、`json`、`csv`、`markdown` 四种 Skill 输出。CSV 必须符合即创任务契约；
JSON 保留结构化审计字段；Markdown 用于人工验证记录；text 用于单条直接结果。请求多个
格式时分别落盘，不得用一种格式覆盖另一种。
