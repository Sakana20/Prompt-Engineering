# 项目协作规范

本文件适用于整个仓库。

## 项目边界

- 本项目负责商品资料、文案 Prompt、成品文案、数字人 Prompt 和下游任务包编排。
- `Auto Oceanengine 26.6.22` 负责即创任务导入、状态机、额度保护、生成、轮询和下载。
- 未经用户明确确认，不触发付费视频提交。
- 不得虚构商品参数、功效、价格、销量、品牌或促销。

## Python 与依赖

- 使用 Python 3.12+。
- 依赖统一使用 `uv`；固定环境为 `/Users/sakana/PyEnv/prompt-engineering`，不使用项目本地 `.venv`、系统 Python 或全局 `pip`。
- 增删依赖使用 `uv add`、`uv add --dev` 或 `uv remove`，不得手改 `uv.lock`。
- 生产代码放在 `src/avatar_prompt_pipeline/`。

## 工程规则

- 外部边界与公共函数必须提供完整类型标注，并通过 mypy strict。
- 领域模型使用不可变 dataclass 或明确的类型，不传播无结构字典。
- Prompt 模板是版本化资源；模板变更必须更新测试和文档。
- 文件写入使用 UTF-8、原子替换；CSV 使用标准库正确处理引号与换行。
- Codex 负责全部语义分析和 Prompt 生成；不得接入其他 LLM 或模型 API。
- 确定性校验、下游写入和视频执行必须分层，便于独立测试和人工接管。
- 不把 Cookie、Token、验证码、签名、个人数据或真实业务凭据写入仓库。

## 测试

- `tests/unit/`：纯函数、校验、模板和领域模型。
- `tests/integration/`：文件系统、任务包、下游 CSV 合约。
- `tests/e2e/`：CLI 用户入口；默认不得访问网络或付费流程。
- `tests/cases/`：前向验证记录、脱敏样本和 golden cases。
- 所有测试产物与验证报告统一放在 `tests/`，不得放入 `docs/`。
- 每次行为变更同时补充相应测试。
- Skill 结构变更后运行 `skill-creator` 的 `quick_validate.py`。

提交前运行：

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

## 文档同步

每次变更检查并按需更新 `README.md`、`docs/architecture.md`、
`docs/implementation-plan.md`、`docs/development.md` 和 `docs/feasibility-study.md`。

## Codex 本地同步（强制）

- 每次修改生产代码、CLI、Prompt 模板、Schema 或 `prompt-engineering/` Skill 后，任务都不算
  完成，直到仓库最新版已同步安装到
  `/Users/sakana/.codex/skills/prompt-engineering`。
- 同步前先完成 Ruff、mypy、pytest；Skill 内容或结构有变化时还必须运行
  `skill-creator` 的 `quick_validate.py`。
- 安装源必须是当前工作区的 `prompt-engineering/`，不能只依赖尚未包含本地修改的 GitHub
  版本。覆盖已安装目录前先创建可恢复备份。
- 安装后运行
  `diff -qr prompt-engineering /Users/sakana/.codex/skills/prompt-engineering`；只有无差异才算
  同步成功。
- 安装后通过已安装 Skill 的 `scripts/run_cli.py -- --help` 验证本地 CLI，确认新增或修改的
  命令已经可见。
- 最终回复必须报告测试、Skill 校验、安装目录比对和 CLI 验证结果；不得只说明仓库已修改。
