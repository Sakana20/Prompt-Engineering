# 开发规范

## 环境管理

仅使用 `uv`：

```bash
uv sync --dev
uv run avatar-prompts --help
```

本项目固定使用 `/Users/sakana/PyEnv/prompt-engineering`：

```bash
export UV_PROJECT_ENVIRONMENT=/Users/sakana/PyEnv/prompt-engineering
```

不要使用项目本地 `.venv`、系统 Python 或全局 pip。

## 常用命令

```bash
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest
uv run pytest tests/unit
uv run pytest -m integration
uv run pytest -m e2e
uv run python tools/skill_reviewer/server.py
uv run avatar-prompts validate-batch --input generated-task-batch.json --preset none
uv run avatar-prompts package --input generated-task-batch.json --format json --preset none
uv run avatar-prompts init-batch --task-name demo --category 水果 --output demo.tasks.json
uv run avatar-prompts export-csv --input demo.tasks.json --preset none
```

`tools/skill_reviewer/` 是本地人工审核台。它会扫描
`/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材/Codex` 下的 CSV，并自动匹配同目录
SQLite 作为状态来源；也支持用户在页面里手动选择 CSV。SQLite 只读读取 `jobs.status`，
按 `task_id` 合并到 CSV 行上。每日列表优先用 CSV `notes` 字段前缀聚合批次名，真实文件名
作为次级信息展示。高亮颜色和自定义短语保存在浏览器 `localStorage`，不写回 CSV、数据库
或下游项目。

每日 ASR 学习素材与上述 CSV 入口分开：默认目录为
`/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材`。`learning-transcribe` 省略
`--input` 时用本地日期或 `--date` 解析该目录，只扫描当前一层。审核台加载、刷新和审核操作
都不得自动触发转写。

## 代码标准

- Python 3.12+，公共边界完整类型标注；
- mypy strict，不以无意义 `Any` 或 ignore 逃避建模；
- 领域对象默认不可变；
- 外部数据先校验再进入领域层；
- Codex 生成结果必须先通过 `generated-task-batch.schema.json` 对应的严格 loader，未知字段
  不得静默丢弃；
- Agent 只填写 `init-batch` 生成的 JSON，不新增临时 CSV 脚本；所有 CSV 必须通过
  `export-csv` 或 `package --format csv` 调用项目 writer；
- 文件路径使用 `pathlib.Path`；
- 用户内容以 UTF-8 保存；
- 错误信息说明阶段、原因和可恢复动作；
- 日志及测试夹具不得包含凭据或真实业务敏感数据。

## 测试策略

学习功能测试默认使用可注入 fake worker，不加载真实 Paraformer。测试必须覆盖 copy/person
隔离、原文不可变、revision 冲突、状态机、路径穿越、worker 超时与非法 JSON、缓存复用、
单项失败、未批准拒绝发布、事务回滚、learned 资源进入 Prompt、空资源兼容、审核台旧 API
回归和学习 API 409。真实素材 smoke test 只在用户明确提供短媒体后运行。

不得在 FunASR 仓库运行测试或格式化；执行 Prompt-owned worker 前后分别记录其
`git status --short`，结果必须完全相同。

### 单元测试

覆盖领域校验、模板替换、空文案、防 NUL 字符和序列化。单元测试不访问网络和真实文件
系统边界。

口播校验还需覆盖 `NO_SPLIT` 标签完整性、标签不计字数、标签包装幂等性，以及数字人
Prompt/CSV 边界移除标签。集成测试必须证明字幕稿 writer 与 CSV writer 可以分别调用、
互不创建对方文件，并且均拒绝覆盖已有文件。
淘宝闪购合规校验还需覆盖阿拉伯整数、小数、中文数字和前后置红包金额，并证明模糊利益点以及
与红包无关的已确认商品价格不会误报；项目集成测试还必须确认其品类为美食外卖、风格为
`benefit-forward-promo`，并允许 25 元项目式自然行动引导。

跑量批次支持 `source_fill`、`human_rewrite` 与 `natural_generate`。测试保证 10 条时
`human_rewrite` 严格为 5 条，奇数批次按 `floor(N/2)` 计算 AI 改写数。只有来源轨具备
`source_block_id`，且同轨来源不重复。每条
AI 改写必须登记至少两个 `rewrite_anchor_phrases`，测试验证所有登记字眼确实存在于成稿。
新清单的直接填槽任务必须登记 `source_slot_values`；测试覆盖固化原文块 ID、饮品拒绝固体食品
直填块、饮品拒绝饱腹句、活动信息不得进入商品插槽，以及套餐组成与活动句正确分层时放行。
直接填槽轨保留原句顺序；AI 改写轨必须贴近具体原文块的字眼和说话逻辑，禁止恢复旧版抽象
片段模板。两轨均不得嵌入样本金额、红包、价格或活动利益点，且必须执行当前活动校验。
时间语境测试必须传入固定日期，覆盖四季映射、夏季拒绝残留冬季表达的成稿、匹配季节
放行，以及 AI 改写跨季参考块后以非季节性锚点重建当季情境的放行。未经
确认的当前天气拒绝、`confirmed_claims` 明确确认后放行。生产运行默认使用本地当天日期。

### 集成测试

使用 pytest 临时目录验证 JSON、字幕稿和 CSV 原子落盘及双文件合约。不得增加其他
LLM provider。

### 端到端测试

从 CLI 参数进入，验证退出码、标准输出和文件产物。默认不得操作浏览器或即创。
任何真实 E2E 都必须通过显式环境开关启用，并不得默认触发付费。

`package` E2E 还必须验证：全批校验失败时零写入、目标冲突时拒绝覆盖、只生成显式选择的
格式、`notes` 使用真实品类与 1-based 序号，以及状态中不声称已提交付费生成。

### Skill 验证

每次修改 `prompt-engineering/` 后运行官方 `quick_validate.py`。测试还应检查 Skill 名称、
frontmatter、UI 元数据及全部必需
reference 文件，避免开发仓库正常但分发目录残缺。

### 测试资料归档

所有前向验证记录、脱敏输入、预期输出、golden cases 和测试报告统一放在 `tests/`。
其中人工可读的品类验证记录放在 `tests/cases/`；`docs/` 只保留长期有效的架构、计划和
开发规范。

## 变更清单

每次实现行为变更时：

1. 添加或更新测试；
2. 更新相关文档；
3. 运行 format、lint、mypy 和完整 pytest；
4. Skill 内容或结构变化时运行 `quick_validate.py`；
5. 将当前工作区的 `prompt-engineering/` 同步安装到
   `/Users/sakana/.codex/skills/prompt-engineering`，安装前保留可恢复备份；
6. 运行目录比对和已安装 CLI 验证：

   ```bash
   diff -qr prompt-engineering /Users/sakana/.codex/skills/prompt-engineering
   /usr/bin/python3 \
     /Users/sakana/.codex/skills/prompt-engineering/scripts/run_cli.py \
     --python-executable /Users/sakana/PyEnv/prompt-engineering/bin/python \
     -- --help
   ```

7. 检查没有生成物、凭据和用户数据进入版本控制；
8. 清楚标注哪些能力已实现、哪些仍是计划。

代码修改完成但本地已安装 Skill 尚未同步，视为任务未完成。同步源必须是当前工作区，而
不是可能尚未包含本地修改的远端分支。最终交付说明必须明确报告测试、Skill 校验、目录
比对和 CLI 验证结果。
