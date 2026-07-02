# Taobao Avatar Video Codex Skill

这是 `taobao-avatar-video` Codex Skill 的开发仓库。Codex 直接分析商品资料、生成淘宝
闪购口播与数字人 Prompt，并为 `Auto Oceanengine 26.6.22` 准备可审计任务包。

可分发 Skill 位于 [taobao-avatar-video](taobao-avatar-video/)：

1. `SKILL.md` 定义触发条件与执行流程；
2. `references/` 保存已验证文案规则、数字人规则和即创契约；
3. `agents/openai.yaml` 提供 Codex UI 元数据。
4. `scripts/run_cli.py` 透明保留全部现有 CLI 参数。
5. JSON Schema 描述 CLI 参数与 Skill 配置、批处理、插件、调试和输出格式。

不接入其他 LLM 或模型 API。仓库中的 Python 只承担确定性编排、校验、序列化和未来 CSV
导出，不负责语义生成。写入下游、导入任务和付费视频生成仍是独立授权边界。

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
  taobao-avatar-video
```

Skill CLI 透明入口：

```bash
python taobao-avatar-video/scripts/run_cli.py -- compose --category 西瓜
python taobao-avatar-video/scripts/run_cli.py --debug -- validate-copy '完整口播正文'
```
