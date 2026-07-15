# Commerce Avatar Content

这是通用商品数字人内容项目。Codex 直接分析商品与活动资料，生成商品口播、数字人
Prompt、字幕稿和任务 CSV。项目分发为一个通用化 Codex Skill，保留淘宝闪购默认利益点
作为兼容预设。

可分发 Skill：

- [prompt-engineering](prompt-engineering/)：通用商品数字人内容入口，支持 0–3 条利益点、
  无利益点任务，以及 `taobao-instant-commerce-default` 兼容预设。

Skill 包含：

1. `SKILL.md` 定义触发条件与执行流程；
2. `references/` 保存已验证文案规则、数字人规则和即创契约；
3. `agents/openai.yaml` 提供 Codex UI 元数据。
4. `scripts/run_cli.py` 透明保留全部现有 CLI 参数。
5. JSON Schema 描述 CLI 参数与 Skill 配置、批处理、插件、调试和输出格式。

利益点来自用户输入或已确认预设。CLI 使用 `--benefit-point` 覆盖默认利益点，使用
`--preset none` 创建无利益点任务；不得自行创造促销、金额或门槛。
也可以使用一个项目一个 JSON 配置文件的方式固化完整项目口径。配置文件放在
`configs/projects/`，包含商品资料、
平台、活动名、利益点、互斥或禁用表达、确认可用信息、校验配置路径、语言风格；适合“淘宝闪购 12 元无门槛红包”和“淘宝闪购
25 元无门槛红包”这类不能混用的项目。传入 `--config` 后，不再自动加载默认淘宝利益点，
也不要同时传入 `--benefit-point`、`--preset`、`--platform` 或 `--campaign-name`。
配置了 `platform` 时，每条口播必须逐字出现平台名；淘宝闪购项目不能省略“淘宝闪购”。
仓库已提供两个可运行样例，默认品类为“西瓜”；正式项目使用前应复制并改成用户确认的
真实品类、商品名和卖点。
其中 `configs/projects/taobao-12-no-threshold-redpacket.json` 同时作为
`taobao-instant-commerce-default` 兼容预设的数据源。

不接入其他 LLM 或模型 API。仓库中的 Python 只承担确定性编排、校验、序列化和产物
写出，不负责语义生成。写入下游、导入任务和付费视频生成仍是独立授权边界。

生成态口播按活动契约使用 `[[NO_SPLIT]]…[[/NO_SPLIT]]` 包裹指定利益点，标签不计入口播
字数。
口播定位为“商品导向的生活化分享”：场景约占 20%，商品与选择理由约占 50%，利益点和
具体购买体验约占 30%，避免写成完整生活故事。
所有产物按 `/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/`
分层。同一任务目录同时保存带标签的 `<task_id>.smartsplit.txt` 和去掉标签的
`<task>.csv`。两类文件分别生成、互不触发、互不覆盖。

批量生成时，每条 Prompt 必须使用不同人物和不同服装；人物可以不同，但保持年轻、自然、
干净、生活化的统一账号审美。

## 环境

项目使用 Python 3.12+ 和 `uv`：

```bash
uv sync --dev
uv run avatar-prompts compose --category 雨靴 \
  --product-name 浅卡其色中筒雨靴 \
  --selling-point 浅卡其配色 \
  --selling-point 中筒款式
```

也可写入 JSON 文件：

```bash
uv run avatar-prompts compose --category 雨靴 --output output/rain-boots.json
```

使用项目配置文件：

```json
{
  "project_id": "taobao-25-no-threshold-redpacket",
  "category": "西瓜",
  "platform": "淘宝闪购",
  "campaign_name": "25元无门槛红包项目",
  "benefit_points": [
    {
      "id": "primary-benefit",
      "text": "最高25元无门槛红包",
      "required": true,
      "exact_match": true,
      "no_split": true,
      "priority": 1
    }
  ],
  "campaign_forbidden_expressions": ["最高12元无门槛红包"],
  "confirmed_claims": ["可提及配送到家或外卖到家", "可提及闪购新人福利"],
  "validation_config_path": "../validation/taobao-25-promo.json",
  "language_style": {
    "name": "benefit-forward-promo",
    "tone": "短视频投流口吻，福利感强，语气可以更兴奋直接，但必须围绕已确认权益表达",
    "point_of_view": "像刚发现淘宝闪购福利后，直接提醒朋友去领、去看、去下单",
    "sentence_style": "开头快速点出人群或商品场景，随后连续给出福利点，句子短促有节奏",
    "emphasis": ["先让用户听清楚本次活动利益点，再回到商品使用场景"],
    "avoid_phrases": ["薅羊毛", "错过就亏", "赶紧领"],
    "extra_rules": ["不要暗示活动长期有效"]
  }
}
```

```bash
uv run avatar-prompts compose --config configs/projects/taobao-25-no-threshold-redpacket.json
uv run avatar-prompts validate-copy '完整口播正文' \
  --config configs/projects/taobao-25-no-threshold-redpacket.json
```

校验 Codex 生成的口播：

```bash
uv run avatar-prompts validate-copy '完整口播正文'
```

## 质量检查

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

## 文档

- [可行性研究](docs/feasibility-study.md)
- [架构设计](docs/architecture.md)
- [实现计划](docs/implementation-plan.md)
- [开发规范](docs/development.md)
- [“西瓜”品类前向验证](tests/cases/validation-watermelon.md)

## Skill 验证

```bash
uv run python /Users/sakana/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  prompt-engineering
```

Skill CLI 透明入口：

```bash
python prompt-engineering/scripts/run_cli.py -- compose --category 西瓜
python prompt-engineering/scripts/run_cli.py --debug -- validate-copy '完整口播正文'
```
