# Prompt Engineering

Prompt Engineering 是商品短视频内容与数字人任务包项目。它负责把用户确认的商品事实、
活动口径和利益点整理成可审计的口播文案、数字人首帧 Prompt、SmartSplit 字幕稿、
Auto Oceanengine CSV，以及 LibTV OmniHuman 任务包。

本项目只做内容生成、确定性校验和文件交接；不登录平台、不提交付费生成、不导入即创任务。
Auto Oceanengine、LibTV 等下游执行器必须由用户另行确认后再运行。

## 当前能力

- 生成 80-100 字中文商品口播，支持通用商品、淘宝闪购默认利益点、无利益点任务，以及
  一个项目一个 JSON 配置文件的完整活动口径。
- 直接固化人工跑量原稿中可复用的真人正文块：只填当前商品事实插槽，保留原句、原顺序、
  重复和口语停顿，不再由模型提炼文风或仿写新句；原稿中的价格、红包、活动、平台权益、
  配送、赠品和行动引导不进入正文块，成稿利益点只取当前任务配置。
- 生成 Prompt 自动注入当前本地日期、月份和季节；校验器拒绝跨季节场景，并拦截任务未确认
  的实时天气描述。
- 校验活动利益点、平台名、禁词、行动引导、`[[NO_SPLIT]]` 标签完整性和批量文案相似度。
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
