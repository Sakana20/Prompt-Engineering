# 开发规范

## 环境管理

仅使用 `uv`：

```bash
uv sync --dev
uv run avatar-prompts --help
```

如需使用独立环境，优先放在 `/Users/sakana/PyEnv`，通过
`UV_PROJECT_ENVIRONMENT=/Users/sakana/PyEnv/<name>` 指定，不使用全局 pip。

## 常用命令

```bash
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest
uv run pytest tests/unit
uv run pytest -m integration
uv run pytest -m e2e
```

## 代码标准

- Python 3.12+，公共边界完整类型标注；
- mypy strict，不以无意义 `Any` 或 ignore 逃避建模；
- 领域对象默认不可变；
- 外部数据先校验再进入领域层；
- 文件路径使用 `pathlib.Path`；
- 用户内容以 UTF-8 保存；
- 错误信息说明阶段、原因和可恢复动作；
- 日志及测试夹具不得包含凭据或真实业务敏感数据。

## 测试策略

### 单元测试

覆盖领域校验、模板替换、空文案、防 NUL 字符和序列化。单元测试不访问网络和真实文件
系统边界。

口播校验还需覆盖 `NO_SPLIT` 标签完整性、标签不计字数、标签包装幂等性，以及数字人
Prompt/CSV 边界移除标签。集成测试必须证明字幕稿 writer 与 CSV writer 可以分别调用、
互不创建对方文件，并且均拒绝覆盖已有文件。

### 集成测试

使用 pytest 临时目录验证 JSON、字幕稿和 CSV 原子落盘及双文件合约。不得增加其他
LLM provider。

### 端到端测试

从 CLI 参数进入，验证退出码、标准输出和文件产物。默认不得操作浏览器或即创。
任何真实 E2E 都必须通过显式环境开关启用，并不得默认触发付费。

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
4. 检查没有生成物、凭据和用户数据进入版本控制；
5. 清楚标注哪些能力已实现、哪些仍是计划。
