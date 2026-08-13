# 每日视频 ASR 文案学习与按需人物 Prompt 学习设计

> 本文档同时是下一次 Codex 对话的实施任务书。执行时以“Codex 执行契约”和“完成定义”为
> 强制要求；后续章节用于解释领域规则和界面细节。若实现过程中发现现状与本文不一致，应先用
> 只读检查确认，再选择兼容方案，不得静默缩小功能或改变边界。

## 新对话启动语

在新对话中可以直接发送：

```text
请完整阅读并执行 docs/daily-video-asr-learning-design.md。
这次不是继续写方案，而是按文档的 Codex 执行契约实现全部功能、测试、工作台、文档和 Skill
同步。先检查 AGENTS.md、git 状态和测试基线，然后按 Step 0 到 Step 7 连续推进；不要只完成
脚手架或只返回计划。不得修改现有字幕入口，不得触发视频生成或付费提交。如果某个方案需要
写入 FunASR 目录，请停止该方向并改为使用本文规定的 Prompt Engineering 自有 worker；
FunASR 仓库必须保持完全只读。
```

## Codex 执行契约

### 本次执行目标

在现有 Prompt Engineering 项目中完整实现两个互相独立的功能，并完成测试、文档、Skill
同步和本地安装验证：

1. **每日视频 ASR 文案学习**：用户显式提供视频或目录后，CLI 调用本地
   FunASR/Paraformer 生成候选识别稿；用户可在学习审核工作台对照原始识别稿修改、保存并
   “提交学习”；该显式人工动作直接批准候选，再由 Codex 生成发布清单并通过 CLI 发布；
2. **按需人物 Prompt 学习**：只有用户主动输入人物 Prompt 时才创建候选；用户可在同一学习
   审核工作台的独立页面修改、保存并“提交学习”；提交后由 Codex 生成发布清单并通过 CLI 发布。

这两个功能必须使用独立命令、独立目录、独立 schema、独立状态记录和独立正式资源。运行其中
一个功能不得读取、创建、修改或发布另一个功能的候选。

### 已确定的架构决策

下一位 Codex 不需要重新讨论以下决策，直接按此实现：

- 不创建新的 Prompt Engineering 顶层 CLI；继续扩展 `avatar-prompts`；
- 不自动扫描或下载网络视频；只处理用户显式传入的本地文件或目录；
- 不把 ASR 文本直接追加到 `docs/learn.txt`；原始识别稿必须不可变，正式库只接收人工批准内容；
- 人物 Prompt 不是每日任务，不跟随 ASR 运行，也不从视频中自动提取；
- 不复制 Paraformer 推理实现到 Prompt Engineering，不给 Prompt Engineering 增加 `funasr`
  或 `torch` 依赖；
- Prompt Engineering 通过无 shell 的 `subprocess` 参数数组，使用 FunASR 已存在的
  `.venv/bin/python -B` 执行本项目自有的纯转写 worker，并严格校验 worker JSON；
- FunASR 项目完全只读：不得新增、修改、格式化、生成或删除其中任何文件，包括
  `pyproject.toml`、源码、脚本、测试、锁文件和缓存；
- 可视化审核台保留原任务审核工作台的只读行为，通过顶部按钮切换到可写的学习审核工作台；
- CLI 和服务端只负责确定性状态、校验和写入；候选文本到正式文案块、人物描述块的语义拆解由
  Codex 完成并写入发布清单；
- 未批准候选不得发布；任何发布失败都不能部分修改正式资源；
- 不触发下游导入、视频生成或付费提交。

### 开始工作前必须读取

按顺序读取并遵守：

1. 仓库根目录 `AGENTS.md`；
2. 本文档全文；
3. `docs/architecture.md`、`docs/implementation-plan.md`、`docs/development.md`；
4. `src/avatar_prompt_pipeline/cli.py`、`source_blocks.py`、`validation.py`、`batch.py`；
5. `src/avatar_prompt_pipeline/templates/avatar_prompt.txt`；
6. `prompt-engineering/SKILL.md`；
7. `prompt-engineering/references/runtime.md`、`volume-copy-source-blocks.md`、
   `source-block-contracts.md`、`avatar-rules.md`；
8. `tools/skill_reviewer/index.html`、`app.js`、`server.py`、`styles.css`；
9. 只读检查 FunASR 的 `pyproject.toml`、`src/funasr_timeline/audio.py`、
   `src/funasr_timeline/asr/base.py` 和 `asr/paraformer_zh_service.py`。

先运行 `git status --short`，保留并避开用户已有改动。不得清理或覆盖不属于本任务的文件。
同时记录 FunASR 仓库的 `git status --short` 基线，任务结束时结果必须完全相同。

### 禁止事项

- 不连接其他 LLM、文案模型、视觉模型或远程 ASR API；
- 不通过 `sys.path` 注入或绝对源码 import 跨项目内部模块；
- 不写入 FunASR 仓库，不运行会在 FunASR 仓库生成缓存、格式化结果或其他文件的命令；
- 不使用 `shell=True`，不拼接可执行命令字符串；
- 不允许浏览器提交任意目标路径；
- 不允许修改不可变的 `raw_transcript` 或 `raw_prompt`；
- 不允许后台或无人操作自动批准候选；网页“提交学习”是用户显式批准动作；
- 不把识别出的价格、促销、品牌、功效、销量或配送话术当作事实；
- 不让人物学习块覆盖固定镜头、商品摆放、无 logo、无字幕和人物稳定性约束；
- 不因为实现新工作台而破坏现有 CSV/SQLite 审核功能；
- 不为了通过测试删除或放宽现有验证规则。

## 实施顺序

除非遇到真实阻塞，按以下顺序连续完成，不要只实现数据模型或只画界面。

### Step 0：基线与目录设计

1. 运行现有 Ruff、mypy、pytest，记录基线；
2. 检查工作区未提交修改；
3. 在 `src/avatar_prompt_pipeline/learning/` 新建学习领域包，生产逻辑不得塞进
   `tools/skill_reviewer/server.py`；
4. 默认运行根目录固定为仓库内 `learning/`，允许 CLI 和审核台显式覆盖，但覆盖路径必须在
   用户指定根目录内解析；
5. 将 `learning/` 运行产物加入 `.gitignore`，测试 fixture 仍放在 `tests/`。

建议生产文件划分如下；可因现有代码结构微调，但职责不得混合：

```text
src/avatar_prompt_pipeline/learning/
  __init__.py
  models.py          不可变领域模型、枚举和显式类型
  store.py           路径解析、原子读写、revision 和审计事件
  asr_provider.py    子进程 provider 协议与严格 JSON 解析
  funasr_worker.py   在 FunASR 既有虚拟环境中执行的只读桥接 worker
  service.py         两类候选的用例编排
  validation.py      状态转换、风险、重复和发布前校验
  publication.py     发布清单校验与全有或全无写入
```

### Step 1：候选领域模型与存储

实现两个不同 dataclass，不传播无结构字典：

- `CopyLearningCandidate`，`kind="copy_transcript"`；
- `PersonPromptLearningCandidate`，`kind="person_prompt"`。

两者可以共享：

- `CandidateId`；
- `LearningStatus`；
- `Revision`；
- `AuditEvent`；
- 原子 JSON writer 和安全路径解析器。

每个候选使用独立目录和一个权威 `candidate.json`，不要把可变状态集中写入一个全局 JSONL。
列表接口通过受限目录扫描或只读索引生成。推荐结构：

```text
learning/copy/candidates/<candidate_id>/
  candidate.json
  source.json
  raw_transcript.txt
  edited_transcript.txt
  word_timeline.json
  asr_report.json
  audit/<revision>.json

learning/person/candidates/<candidate_id>/
  candidate.json
  raw_prompt.txt
  edited_prompt.txt
  audit/<revision>.json
```

写入要求：

- UTF-8；
- 同目录临时文件后原子替换；
- 新候选拒绝覆盖；
- 更新必须携带 `expected_revision`；
- revision 不匹配返回冲突，不能最后写入者覆盖前者；
- 服务端根据 `kind + candidate_id` 解析路径，客户端不能提供目标文件路径；
- 候选 ID 只能使用安全 ASCII 字符；
- 每次保存和状态转换创建独立审计事件。

### Step 2：Prompt Engineering 自有的纯转写 worker

FunASR 当前已有通用 `prepare_audio_for_asr(...)` 和
`ParaformerZhAsrService.transcribe(...)`，但没有无原稿的正式命令。不得因此修改 FunASR。
在 Prompt Engineering 的 `src/avatar_prompt_pipeline/learning/funasr_worker.py` 新增一个
自包含桥接 worker，使用 FunASR 已存在的虚拟环境 Python 执行。worker 的职责仅为：

1. 接收一个本地媒体文件、输出 JSON、模型目录和设备；
2. 在 FunASR 环境中正常 import 已安装的 `funasr_timeline` 包，不修改 `sys.path`；
3. 调用 `prepare_audio_for_asr` 处理视频或非 MP3 音频；
4. 调用 `ParaformerZhAsrService`；
5. 只在 Prompt Engineering 的候选临时目录写转换音频和结果；
6. 原子写出 worker JSON；
7. 不执行分句、原稿匹配、字幕渲染或其他下游步骤。

执行命令契约：

```bash
/Users/sakana/Desktop/Work/Codex/FunASR/.venv/bin/python \
  -B \
  "/Users/sakana/Desktop/Work/Codex/Prompt Engineering/src/avatar_prompt_pipeline/learning/funasr_worker.py" \
  --input /absolute/path/to/video.mp4 \
  --output /absolute/path/to/result.json \
  --work-dir /absolute/path/inside/prompt-engineering/learning/copy/work \
  --model-dir /Users/sakana/PyEnv/paraformer \
  --device mps
```

命令中的 worker 路径应由安装后的 `asr_provider.py` 根据自身包位置解析，不能假设开发工作区
永远存在。`--output` 和 `--work-dir` 必须位于 Prompt Engineering 传入的候选工作目录，绝不
指向 FunASR 仓库。

worker JSON 至少包含：

```json
{
  "schema_version": "1.0",
  "provider": "paraformer-zh",
  "model": "paraformer-zh:/Users/sakana/PyEnv/paraformer",
  "source_media": "/absolute/path/to/video.mp4",
  "asr_audio": "/absolute/path/to/converted-or-original.mp3",
  "audio_conversion": {},
  "text": "识别全文",
  "tokens": [
    {"index": 0, "text": "字", "start_ms": 0, "end_ms": 120, "source": "paraformer-zh"}
  ]
}
```

Prompt Engineering 的 `asr_provider.py` 必须：

- 使用参数数组和 `subprocess.run(..., shell=False)`；
- 默认调用以上 `<FunASR>/.venv/bin/python -B <prompt-owned-worker>`；
- 给子进程设置 `PYTHONDONTWRITEBYTECODE=1`，禁止在 FunASR 源码目录生成 `__pycache__`；
- 允许测试注入 worker command；
- 设置合理超时并截断错误输出；
- 不输出环境变量、密钥或完整敏感命令上下文；
- 检查退出码、结果文件存在性、schema version、provider、text 和每个 token；
- 将 worker 原始结果归档后再创建候选；
- 单个视频失败只创建失败报告，不影响同批其他视频。

worker 文件属于 Prompt Engineering，必须通过本项目 Ruff、mypy 和测试。它可以用动态 import
与明确 Protocol/cast 隔离外部运行时类型，但公共边界仍须有完整类型标注。不得为方便 mypy 而
把 FunASR 安装进 Prompt Engineering 环境，也不得在 FunASR 项目创建 console script。

运行前后比较 FunASR 的 `git status --short` 基线；必须完全一致。如果外部 Python 仍在 FunASR
目录产生新的缓存或文件，立即停止并修复 worker 的环境隔离；不得把新增文件留在 FunASR。

### Step 3：CLI 合约

在现有 `avatar-prompts` 下新增以下命令，并同步
`prompt-engineering/references/cli-parameters.schema.json`、运行时文档、Skill 和测试。

#### 每日文案 ASR

```bash
avatar-prompts learning-transcribe \
  --input /path/a.mp4 \
  --input /path/b.mp4 \
  --learning-root /path/to/learning \
  --date YYYY-MM-DD
```

- `--input` 可重复；每项可以是文件或目录；
- 目录只扫描当前一层的受支持媒体，不默认递归；
- 内容指纹、worker 配置和转换配置共同决定缓存；
- 相同指纹和配置的成功结果复用，不重新识别；
- 输出批次 JSON，总结 succeeded、reused、failed 和 candidate IDs；
- 任何一次运行都不得创建 `learning/person/` 内容。

#### 按需人物 Prompt

```bash
avatar-prompts learning-add-person-prompt \
  --text "人物 Prompt 正文" \
  --source-label "用户人工样本" \
  --learning-root /path/to/learning
```

同时支持 `--input UTF-8.txt`，但 `--text` 与 `--input` 必须互斥。该命令只创建一个
`person_prompt` 候选，不调用 ASR，也不读取 `learning/copy/`。

#### 查询、编辑和状态转换

```text
learning-list    --kind copy|person [--status ...]
learning-preflight --learning-root ...
learning-update  --kind copy|person --candidate-id ... --expected-revision ... --edited-file ...
learning-submit-review --kind copy|person --candidate-id ... --expected-revision ...
learning-approve --kind copy|person --candidate-id ... --expected-revision ...
learning-reject  --kind copy|person --candidate-id ... --expected-revision ... --reason ...
learning-publish --kind copy|person --candidate-id ... --expected-revision ... --manifest ...
```

规则：

- `learning-update` 只修改 edited 内容和允许编辑的结构化字段；
- `learning-submit-review` 将 `pending`/`editing` 转为 `ready_for_review`；
- `approve` 只接受 `ready_for_review`；
- `publish` 只接受 `approved`，且 manifest 中的 candidate ID、kind 和 revision 必须完全一致；
- `reject` 保留原始内容和审计记录，不物理删除；
- 所有命令输出稳定 JSON，成功为 0、验证失败为 1、参数/输入错误为 2；
- 六个生产命令在业务处理前自动执行 `learning-preflight`；有 approved 候选或 published 正式
  块不一致时返回 3，输出完整候选和 Codex 必须完成的 `required_actions`，且不读取或写入原
  生产命令的业务文件；
- 新参数必须出现在 CLI schema 和 Skill 透明启动器帮助中。

### Step 4：发布清单与正式资源

CLI 不自行从自然语言提取语义块。Codex 读取已批准候选后，生成符合 schema 的发布清单，再由
`learning-publish` 确定性校验和落盘。

相关正式资源：

```text
prompt-engineering/references/copy-learning-candidate.schema.json
prompt-engineering/references/person-prompt-learning-candidate.schema.json
prompt-engineering/references/learning-publication.schema.json
prompt-engineering/references/volume-copy-source-blocks.md
prompt-engineering/references/person-prompt-source-blocks.md
prompt-engineering/references/person-prompt-block-contracts.md
```

文案发布清单至少包含：

- candidate ID、revision、source fingerprint；
- 新 `source_block_id`；
- 原句块和强类型插槽；
- 品类族、消费需求、季节限制；
- `source_fill` / `human_rewrite` 适用性；
- 已删除的价格、促销、品牌、功效和行动引导风险项；
- 多样性标签。

人物发布清单至少包含：

- candidate ID、revision；
- identity、hair、outfit、scene 四类块及稳定 ID；
- 允许组合与不兼容组合；
- 已删除的固定约束重复项和风险项；
- 人物与服装多样性标签。

正式资源规则：

- 现有人工块不被重写；新增审核文案块以原有“块标题 + `text` 文案”格式追加到
  `volume-copy-source-blocks.md` 的独立小节，发布清单 JSON 和候选审计字段不进入正式文案库；
- `SKILL.md`、copywriting rules 和生产模板必须从这一统一文案资源读取新增块；
- `source_blocks.py` 的验证注册表必须能识别已发布文案块，不能只更新 Markdown；
- 人物块必须真正进入人物 Prompt 生成指令，不能只保存不使用；
- 人物正式资源与文案一样使用块标题加 fenced `text`，结构化发布信息只保存在 provenance；
  正常生成按类型限量选择，不读取完整人物库；
- 固定人物画面约束始终由现有模板和 validator 提供，learned 人物块只能补充变量；
- 发布前先在内存中生成所有目标内容并完成全部校验，再执行原子替换；
- 任一目标失败时全部保持原样；
- 发布成功后候选变为 `published` 并写入实际 block IDs。

### Step 5：学习审核工作台

修改现有 `tools/skill_reviewer/`，不要新建第二个网站。

必须实现：

- 顶部全局按钮：任务审核时显示“切换到学习审核”，学习审核时显示“返回任务审核”；
- 切换不刷新页面，使用 `localStorage` 保存最后工作台；
- 原任务审核所有现有行为和只读属性保持不变；
- 学习审核默认显示“视频文案”，可切换到独立的“人物 Prompt”页面；
- 视频文案页按日期从 `/Users/sakana/Desktop/Work/2026/<MM.DD>/淘宝闪购/素材` 开始，逐层
  列出文件夹与当前层受支持媒体：日期与扫描控制在左栏，文件夹导航和多选在中间主列表；支持
  进入文件夹和返回上一层，扫描与导航本身不得启动 ASR；
- 静态资源必须禁用缓存；前端连接到缺少每日媒体 API 的旧服务时，必须明确提示重启审核台；
- 用户点击“创建 ASR 候选”后才转写已选媒体，完成后显示新增、缓存复用和失败数量并刷新候选；
- 勾选媒体后在右侧预览最后勾选项；视频和音频使用浏览器原生控件，媒体内容接口支持 Range，
  只能使用服务端扫描得到的 date + directory ID + media ID，预览不得启动 ASR；
- worker 必须清理继承的 Python 环境、使用隔离参数并在识别前预检 FunASR 模块导入；预检或
  识别失败时，页面逐项显示素材名和后端原因并保留失败选择，不得只显示失败数量；FunASR
  `.venv/bin/python` 必须保留符号链接路径，不能 `resolve()` 成基础解释器；
- 文案页显示媒体来源、不可变原文、可编辑稿、风险、相似项、revision 和状态动作；
- 人物页支持“新增人物 Prompt”，并显示不可变原文、可编辑稿、结构化字段、风险、相似项、
  revision 和状态动作；
- 保存时发送 expected revision；409 冲突必须提示用户重新加载，不能覆盖；
- 按状态禁用不允许的按钮；
- 单人工作台只负责保存和“提交学习”，后者作为显式人工批准直接进入 `approved`；兼容 CLI
  仍保留提交审核、批准和驳回，不提供自动发布按钮；
- 已批准详情明确显示“待 Codex 生成发布清单并通过 CLI 发布”；
- 页面在窄屏下不重叠，所有控件使用原生可访问元素。

建议新增专用 API；路径可调整，但语义必须保持：

```text
GET  /api/learning/candidates?kind=copy|person&status=...
GET  /api/learning/candidates/<kind>/<candidate_id>
GET  /api/learning/media?date=YYYY-MM-DD&directory_id=<server-issued-id>
POST /api/learning/transcribe
POST /api/learning/person-candidates
PUT  /api/learning/candidates/<kind>/<candidate_id>
POST /api/learning/candidates/<kind>/<candidate_id>/submit-learning
POST /api/learning/candidates/<kind>/<candidate_id>/submit-review
POST /api/learning/candidates/<kind>/<candidate_id>/approve
POST /api/learning/candidates/<kind>/<candidate_id>/reject
```

服务端要求：

- `--learning-root` 参数默认指向本仓库 `learning/`；
- 所有业务操作调用 `src/avatar_prompt_pipeline/learning/` 服务，不在 HTTP handler 复制规则；
- JSON body 有大小限制和严格类型校验；
- kind、candidate ID 和 revision 均由服务端验证；
- 不接受客户端文件路径；
- 媒体浏览只接受后端返回的目录 ID；媒体转写只接受当前目录扫描结果中的服务端媒体 ID，提交
  时重新校验目录和媒体仍位于当天素材根目录内、媒体属于当前层且格式受支持；
- 只允许 loopback host 的现有默认行为；
- 不把异常堆栈、环境变量或绝对敏感路径返回浏览器。

### Step 6：生成多样性接入

完成发布还不算完成。新增学习块必须实际参与后续生成：

- 文案 Prompt 包从统一的 `volume-copy-source-blocks.md` 读取原人工块与已发布网页学习块；
- 继续满足 `human_rewrite=floor(N/2)` 和三模式字段契约；
- 新增开头类型、节奏、需求和情绪标签的批次集中度预警；
- 人物 Prompt 包读取已发布 identity/hair/outfit/scene 块；
- 在现有年轻、自然、干净、生活化边界内组合，不生成具体真人复刻；
- 继续生成批次唯一 `identity_key` 和 `outfit_key`；
- 增加人物身份标签和服装标签的集中度预警；
- 没有网页发布块或人物 learned 资源时，现有生成结果和 CLI 行为保持兼容。

### Step 7：测试、文档与安装

行为变更必须同时补测试：

```text
tests/unit/test_learning_models.py
tests/unit/test_learning_store.py
tests/unit/test_learning_validation.py
tests/unit/test_learning_publication.py
tests/integration/test_learning_asr_provider.py
tests/integration/test_funasr_worker_contract.py
tests/integration/test_learning_workbench_api.py
tests/integration/test_learning_resources.py
tests/e2e/test_learning_cli.py
```

测试至少覆盖：

- 两类候选不可混写；
- 原始内容不可修改；
- revision 冲突；
- 状态机所有允许和拒绝路径；
- 路径穿越和任意路径写入被拒绝；
- ASR worker 成功、超时、非法 JSON、错误 schema、单项失败和缓存复用；
- 文案 ASR 不创建人物候选；
- 人物输入不调用 ASR；
- 未批准不能发布；
- 多目标发布全有或全无；
- 学习块进入实际 Prompt 编排；
- 无网页发布块或人物 learned 资源时兼容旧行为；
- 原审核台 API 回归；
- 学习审核 API 的读取、保存、409、提交学习直达 approved，以及兼容提交审核、批准和驳回；
- CLI schema 覆盖每个新参数；
- Skill 包含每个新增 reference。

ASR 集成测试默认使用可注入的 fake worker，不加载真实模型。若用户未提供短媒体样本，真实
Paraformer smoke test 不阻塞代码完成，但最终回复必须明确标记“真实素材 smoke test 待用户提供
样本”；不得声称已完成真实识别。

按仓库要求同步更新：

- `README.md`；
- `docs/architecture.md`；
- `docs/implementation-plan.md`；
- `docs/development.md`；
- `docs/feasibility-study.md`（若结论受影响）；
- `prompt-engineering/SKILL.md` 和相关 references；
- `prompt-engineering/references/cli-parameters.schema.json`；
- 生产模板版本和快照/行为测试。

提交前运行：

```bash
UV_PROJECT_ENVIRONMENT=/Users/sakana/PyEnv/prompt-engineering uv run ruff format --check .
UV_PROJECT_ENVIRONMENT=/Users/sakana/PyEnv/prompt-engineering uv run ruff check .
UV_PROJECT_ENVIRONMENT=/Users/sakana/PyEnv/prompt-engineering uv run mypy
UV_PROJECT_ENVIRONMENT=/Users/sakana/PyEnv/prompt-engineering uv run pytest
```

不得在 FunASR 项目运行格式化、测试或其他可能生成文件的命令。只允许读取现有文件和使用其
既有 Python 环境执行 Prompt Engineering 自有 worker。最终报告必须明确给出 FunASR 前后
`git status --short` 一致的结果。

Skill 内容或结构变化后运行 `skill-creator` 的 `quick_validate.py`。随后：

1. 从当前工作区 `prompt-engineering/` 创建可恢复备份后同步到
   `/Users/sakana/.codex/skills/prompt-engineering`；
2. 运行 `diff -qr`，必须无差异；
3. 使用已安装 Skill 的 `scripts/run_cli.py -- --help`，确认所有新增命令可见；
4. 启动本地审核台并完成任务审核/学习审核两种工作台的浏览器验证；
5. 最终回复逐项报告 Ruff、mypy、pytest、Skill quick validation、安装比对、CLI 帮助、工作台
   验证和真实 ASR smoke test 状态。

## 完成定义

只有以下全部成立，任务才算完成：

- [ ] `avatar-prompts --help` 显示全部学习命令；
- [ ] 每日 ASR 能从显式本地媒体创建文案候选，批次可局部失败；
- [ ] FunASR 仓库前后 `git status --short` 完全一致，没有任何新增、修改或删除文件；
- [ ] 按需人物 Prompt 命令只在用户输入时创建人物候选；
- [ ] 两套候选的目录、schema、状态和发布资源完全隔离；
- [ ] 原始 ASR 文本和原始人物 Prompt 不可通过 CLI 或 HTTP 修改；
- [ ] revision 冲突不会覆盖新版本；
- [ ] 未批准候选无法发布；
- [ ] 文案中的样本促销和未确认事实不会进入正式事实层；
- [ ] 人物学习内容不能覆盖固定画面约束；
- [ ] 已发布文案块和人物块实际影响 Prompt 编排；
- [ ] 无学习数据时现有 CLI 和生成行为保持兼容；
- [ ] 审核台顶部可在任务审核与学习审核间切换；
- [ ] 原任务审核仍然只读且功能无回归；
- [ ] 学习审核能修改文案、按需新增人物 Prompt、保存并提交学习；
- [ ] 已批准候选只能由带合法发布清单的 `learning-publish` CLI 发布；
- [ ] 全部工程质量门禁通过；
- [ ] Skill 完成校验、备份安装、目录无差异比对和已安装 CLI 验证；
- [ ] 最终报告没有隐瞒未运行的真实模型或浏览器验证。

## 目标与结论

Prompt Engineering 当前使用固定的真人文案块和人物描述规则。长期运行后，文案开头、句式、
人物长相、发型和服装组合都会逐渐雷同。

本设计包含两个互相独立的功能：

1. **每日视频 ASR 文案学习**：将用户每天选定的参考视频交给本地 FunASR/Paraformer 识别，
   经过人工校对、清洗和审核后，发布为新的真人文案块；
2. **按需人物 Prompt 学习**：只在用户主动提供人物 Prompt 时执行，经过人工编辑、拆解、去重
   和审核后，发布为可组合的人物描述块。它不是每日任务，也不随视频识别自动运行。

两类学习能力都属于 Prompt Engineering，因为它们最终服务于本项目的文案和人物 Prompt
生成。无需新增第二个业务 CLI，应扩展现有 `avatar-prompts` CLI，并复用现有可视化审核台。

两个功能没有输入依赖、调度依赖或批次关联：运行视频 ASR 不创建人物 Prompt 候选；输入人物
Prompt 不扫描视频、不调用 ASR。它们只是在同一个 Prompt Engineering 项目中分别管理。

识别稿和人物 Prompt 都不能未经审核直接进入各自的正式学习库。正式学习库只接收有来源、
有版本、有人工批准记录的内容。

## 项目边界

### Prompt Engineering 负责

- 接收用户明确指定的每日参考视频；
- 编排本地 FunASR 无稿转写；
- 保存不可变的 ASR 原文、人工修订稿和审核状态；
- 接收用户手工输入的人物 Prompt；
- 分别管理文案候选库与人物 Prompt 候选库；
- 提供可视化编辑、保存和提交学习，并提供独立 CLI 发布；
- 执行来源追踪、重复检测、事实隔离和确定性校验；
- 将批准内容发布到对应的 Prompt 资源；
- 在后续生成中调度更多样的文案结构、人物身份和服装组合。

### Prompt Engineering 不负责

- 自动下载、爬取或绕过平台限制获取视频；
- 自动相信视频中的价格、促销、销量、功效、品牌或配送承诺；
- 未经人工确认自动发布学习内容；
- 把文案样本和人物 Prompt 样本混为一个库；
- 用参考 Prompt 覆盖现有画面安全约束、商品摆放约束或批次唯一性规则；
- 触发视频生成、付费提交或下游导入。

现有字幕处理链路不在本功能范围内，不调用、不修改，也不作为本功能的实现入口。

## 为什么放入现有 CLI

现有 `avatar-prompts` 已经负责商品资料、文案 Prompt、人物 Prompt、校验和任务包。学习系统
改变的正是这些生成资源，因此加入现有 CLI 比新建 CLI 更合理：

- 学习库和生成逻辑使用同一套项目版本；
- 审核、发布和生成之间不需要跨项目同步状态；
- 继续通过 Skill 的 `scripts/run_cli.py` 透明调用；
- 保持一套安装环境、一套配置和一套测试入口；
- 可以在发布时直接执行现有文案和人物 Prompt 校验；
- 可视化审核台只需增加工作台切换，不需要维护第二个网站。

实现时增加以下一层 CLI 子命令，不新增顶层可执行程序：

```text
avatar-prompts learning-transcribe
avatar-prompts learning-add-person-prompt
avatar-prompts learning-preflight
avatar-prompts learning-list
avatar-prompts learning-update
avatar-prompts learning-submit-review
avatar-prompts learning-approve
avatar-prompts learning-reject
avatar-prompts learning-publish
```

首版沿用当前 argparse 的扁平子命令风格。将来命令明显增多时，可以兼容增加
`avatar-prompts learning <action>`，但不应为了首版重构全部现有命令。

## 两个独立流程

### 流程一：每日视频 ASR 文案学习

```text
参考视频
  → learning-transcribe
  → FunASR/Paraformer 原始识别
  → 文案候选库
  → 可视化校对、清洗、审核
  → 文案原文块发布
  → 后续文案生成
```

该流程可以每天批量运行，但只处理文案。它不会读取、生成或修改人物 Prompt 候选。

### 流程二：按需人物 Prompt 学习

```text
人物 Prompt 文本
  → learning-add-person-prompt
  → 人物 Prompt 候选库
  → 可视化编辑、拆解、审核
  → 人物描述块发布
  → 后续人物 Prompt 生成
```

该流程没有每日计划。只有用户主动粘贴文本或指定人物 Prompt 文件时才创建候选，且完全不调用
视频 ASR。

两套流程可以复用相同的状态名称和审计基础设施，但各自拥有独立状态记录、schema、校验器、
目录和正式资源。

```text
单人网页：pending → editing → 提交学习/approved → published
兼容 CLI：pending → editing → ready_for_review → approved → published
                                      ↘ rejected
```

只有用户点击“提交学习”或在兼容 CLI 明确执行批准动作才能进入 `approved`。任何后台任务都不能
自动批准。

## 文案视频识别

### 已有底层能力

FunASR 的 Paraformer 服务位于：

```text
/Users/sakana/Desktop/Work/Codex/FunASR/src/funasr_timeline/asr/paraformer_zh_service.py
```

本地模型目录为：

```text
/Users/sakana/PyEnv/paraformer
```

`ParaformerZhAsrService.transcribe(audio_path)` 已能返回：

- `WordTimeline.asr.text`：完整识别文本；
- `WordTimeline.tokens`：字符或 ASCII 词组的起止时间；
- ASR provider、模型目录和音频信息。

Prompt Engineering 不应复制这套识别实现，也不应通过绝对源码路径修改 `sys.path` 后直接
import。按执行契约新增 Prompt Engineering 自有 `funasr_worker.py`，使用 FunASR 的既有
Python 环境正常 import 已安装包；主进程只取得结构化 JSON 并在本项目验证 schema。

### 素材发现与转写

`learning-transcribe` 支持单个文件、多个显式文件或一个明确指定的目录。它不得默认递归扫描
整个工作区。

每个媒体文件执行：

1. 计算内容指纹，避免同一视频改名后重复识别；
2. 用独立媒体适配器抽取 Paraformer 可读取的音频；
3. 调用本地 Paraformer；
4. 保存不可变原始识别结果和词级时间轴；
5. 创建 `copy_transcript` 类型候选；
6. 对空文本、异常时间戳、极短语音和疑似无人声进行标记；
7. 单项失败只记录该项错误，不终止整批。

每个输入至少保存：

```text
source.json
raw_transcript.txt
word_timeline.json
asr_report.json
edited_transcript.txt
candidate.json
```

`raw_transcript.txt` 永远不可覆盖。审核台修改的是 `edited_transcript.txt` 和候选元数据。

### 文案清洗与发布

机器清洗只做可解释的确定性标记，不自动把 ASR 文本润色成新文案：

- 规范空白和明显重复标点；
- 上述规范化只初始化 `edited_transcript`：移除中文逐字分隔空白、保留 ASCII 词组内部单个
  空格并压缩相同重复标点；`raw_transcript`、token 和时间戳保持原样，机器不得补写缺失标点、
  改字或调整大小写；
- 例如原始识别为 `以 前 上 班 我 忍 气 吞 声` 时，初始可编辑稿必须是
  `以前上班我忍气吞声`，不能自动猜成带逗号或句号的润色稿；ASR 已有标点仍应保留，人工补写
  标点或纠错只更新带 revision 的可编辑稿；
- 标记价格、起步价、红包、券、平台活动、配送、退款、赠品和行动引导；
- 标记品牌、功效、销量和具体商品参数；
- 与当天候选、历史候选和正式原文块做精确去重与相似度预警；
- 保留源视频指纹和本地路径引用；
- 无法确认是否可复用时保持风险标记，由人工决定。

发布时不把整段视频文案直接追加到 `docs/learn.txt`。发布动作应生成正式原文块：

- 分配稳定唯一的 `source_block_id`；
- 保留真人原句的停顿、重复、反问、突然开口和口语毛边；
- 删除价格、促销、平台、配送、赠品和行动引导；
- 把允许变化的商品内容转换为强类型插槽；
- 登记品类族、消费需求、季节限制和必需商品事实；
- 标记可用于 `source_fill` 或只能用于 `human_rewrite`；
- 发布后继续执行 `source_slot_values`、活动隔离、食品/饮品动作和季节校验。

`docs/learn.txt` 保留为历史人工原稿，不作为无限追加的数据库。正式生成使用审核通过并版本化的
原文块资源。

## 人物 Prompt 学习

### 输入方式

用户可以通过 CLI 或学习审核工作台直接输入一条或多条人物 Prompt：

```text
avatar-prompts learning-add-person-prompt \
  --input person-prompts.txt \
  --source-label "用户人工样本"
```

也可以在工作台点击“新增人物 Prompt”，在原始 Prompt 文本框中粘贴内容。创建后状态为
`pending`，不会立即影响生产生成。

### 为什么不能直接整段复用

当前静态人物 Prompt 同时包含两类信息：

1. **固定生产约束**：竖屏比例、固定中景、直视镜头、商品摆放、人物不手持或接触商品、
   非商品区域无 logo、无字幕等；
2. **可学习变量**：年龄方向、脸型、五官、人物审美、发型、发色、服装组合和环境风格。

输入的人物 Prompt 只能补充第二类变量，不能覆盖第一类固定约束。否则系统可能为了学习新人物
而破坏现有画面和商品安全规则。

### 人物 Prompt 候选结构

每条候选保留原始 Prompt，同时由 Codex 与人工拆解为可审计字段：

| 字段 | 含义 |
| --- | --- |
| `candidate_id` | 稳定候选 ID |
| `source_type` | 固定为 `manual_person_prompt` |
| `source_label` | 用户填写的来源说明 |
| `raw_prompt` | 不可变原始输入 |
| `edited_prompt` | 人工修订版本 |
| `identity_traits` | 脸型、五官和人物气质 |
| `hair_traits` | 发型、刘海、长度和发色 |
| `outfit_traits` | 上装、下装、颜色和穿搭方向 |
| `scene_traits` | 可复用且不改变固定镜头契约的环境特征 |
| `forbidden_traits` | 不应复用的内容 |
| `risk_tags` | 品牌、logo、年龄、暴露、真实身份等风险 |
| `similarity_hits` | 与正式人物块和历史候选的相似结果 |
| `status` | 当前审核状态 |
| `published_block_ids` | 发布后生成的人物描述块 ID |

不得保存真实人物姓名、联系方式、账号信息、凭据或用于复刻具体个人身份的敏感描述。用户输入
包含品牌 logo、夸张暴露、年龄不明或与项目年轻自然审美冲突时，必须标记并在发布前处理。

### 正式人物描述块

人物 Prompt 的正式学习库应采用模块化描述块，而不是复制完整 Prompt：

```text
identity_block   人物脸型、五官组合和审美方向
hair_block       发型、刘海、长度和发色组合
outfit_block     完整服装搭配及颜色关系
scene_block      与固定口播首帧兼容的背景方向
```

发布时需要：

- 每个块分配稳定 ID 和来源候选 ID；
- 校验人物方向年轻、自然、干净、生活化；
- 排除大妈、中年、老气、暴露、土味、夸张和大面积 logo 方向；
- 拒绝与已有块高度重复的身份和服装描述；
- 保证身份块与服装块可以独立重组；
- 不把固定镜头、商品摆放和安全约束写入学习变量；
- 记录适合搭配的审美方向及不兼容组合。

后续生成仍需为每条任务生成唯一的 `identity_key` 和 `outfit_key`。学习库扩充不能取消批次内
人物身份与服装唯一性校验。

## 两套独立学习库

运行数据与设计文档分开。实现时使用：

```text
learning/
  copy/
    candidates/<candidate_id>/
    rejected/
    published/provenance.jsonl
  person/
    candidates/<candidate_id>/
    rejected/
    published/provenance.jsonl
```

文案候选和人物候选绝不共用同一 schema、清单文件或正式资源。底层可以复用候选 ID 生成、
状态名称、审计记录和原子写入工具，但一次命令或一次状态转换只能操作其中一种候选。列表由
受限目录扫描生成，不使用一个可变的全局 `catalog.jsonl` 作为权威状态。

正式资源建议分别落到：

```text
prompt-engineering/references/volume-copy-source-blocks.md
prompt-engineering/references/source-block-contracts.md
prompt-engineering/references/person-prompt-source-blocks.md
prompt-engineering/references/person-prompt-block-contracts.md
```

执行本任务时必须创建后两份人物学习资源，并同步纳入 Skill、生产 Prompt 编排和测试。

## 可视化审核工作台

### 当前状态

现有 `tools/skill_reviewer/` 是只读任务审核台，主要展示即创/LibTV CSV，并可关联 SQLite 状态。
它当前不适合直接编辑学习候选，也没有学习候选的写入 API。

保留现有任务审核行为，在同一个页面增加第二个“学习审核”工作台。两者共用外层应用，但数据源、
权限和页面状态完全分离。

### 切换工作台按钮

在页面顶部品牌区或全局工具栏增加一个明确的原生按钮：

```text
任务审核状态：  [切换到学习审核]
学习审核状态：  [返回任务审核]
```

按钮属于应用级导航，不放在某个候选详情内部。切换时：

- 不重新加载整个页面；
- 保存当前工作台的搜索条件和选中项；
- 使用 `localStorage` 记录上次打开的工作台；
- 更新页面标题、副标题和空状态说明；
- 使用可见文本说明目标工作台，不使用只有图标的按钮；
- 键盘可操作并保留浏览器默认焦点样式；
- 任务审核工作台继续保持只读。

### 学习审核工作台布局

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Skill 审核台       学习审核                         [返回任务审核] │
├────────────────┬──────────────────────┬──────────────────────────────┤
│ 学习类型       │ 当天素材             │ 候选详情                     │
│ ○ 视频文案     │ □ 今日视频.mp4       │ 来源 / 状态 / 风险 / 相似项  │
│ ○ 人物 Prompt  │ □ 今日音频.wav       │ 原始内容（只读）             │
│ 日期           │ [创建 ASR 候选]      │ 编辑内容                     │
│ [扫描]         │                      │ [保存修改] [提交学习]       │
│ 状态筛选       │ 学习候选             │                              │
│ [+新增人物]    │ 08-12 · pending      │                              │
└────────────────┴──────────────────────┴──────────────────────────────┘
```

文案和人物 Prompt 通过“学习类型”切换，不能在同一详情表单里混合字段。默认进入“视频文案”
列表；人物 Prompt 页面没有“每日”概念，只展示用户曾经主动添加的候选。

### 文案审核详情

文案候选详情至少显示：

- 视频来源、文件指纹、媒体时长和识别时间；
- 原始 ASR 文本，只读；
- 可编辑校对稿；
- 价格、促销、品牌、功效和行动引导风险标记；
- 与历史候选和正式原文块的相似项；
- 建议品类族、消费需求、季节限制和来源块用途；
- 品类族、消费需求和季节必须显示为带中文解释的单选项；来源块用途允许同时选择直接填槽与
  AI 改写参考，使用复选项；提交学习前必须完成品类族、消费需求和至少一种用途并先保存；
- 宽屏下三个单选字段自适应并排、两个来源用途并排，窄屏回退单列；
- 保存和提交学习动作；提交学习后直接显示等待 Codex 发布的 `approved` 状态。

pending、editing、ready_for_review 和 rejected 候选可按 revision 删除。删除为可恢复归档：
整个候选目录移入 `learning/<kind>/trash/`，不删除源素材；对应媒体恢复“未识别”，用户可重新
创建候选。approved 和 published 候选禁止删除，避免破坏已批准或已发布资源的追溯关系。

若浏览器支持本地媒体预览，可以在详情中提供视频或音频播放用于逐句核对；路径无效时显示明确
提示，不影响文本编辑。

### 人物 Prompt 审核详情

人物候选详情至少显示：

- 原始 Prompt，只读；
- 可编辑 Prompt；
- 人物身份、发型、服装、场景的结构化字段；
- 固定约束与可学习变量的对照；
- 品牌、logo、年龄、暴露和具体真人复刻风险；
- 与既有人物块的身份相似度和服装相似度；
- 保存和提交学习动作；提交学习作为用户显式批准，之后显示等待 Codex 发布的状态。

“新增人物 Prompt”打开一个简单编辑区域，只要求 Prompt 正文和可选来源说明。创建成功后进入
详情页，不直接发布。

### 写入安全

学习审核是受控可写功能，不能沿用当前任意数据库展示接口直接写文件。服务端新增专用 API 时
必须满足：

- 只允许访问项目固定的 `learning/` 根目录；
- 候选 ID 必须由服务端解析，客户端不得提交任意目标路径；
- 原始 ASR 文本和原始人物 Prompt 永远不可修改；
- 编辑稿采用 UTF-8 原子写入；
- 每次保存带 `revision`，旧 revision 提交时拒绝覆盖；
- 状态转换在服务端校验，未批准候选不能发布；
- 保存、提交学习以及后续 CLI 发布都写入审计记录；兼容 CLI 的提交审核、批准、驳回仍保留审计；
- 发布前完成全量校验，失败时不修改正式资源；
- 工作台不得触发视频生成、导入或付费提交。

## 多样性调度

增加样本数量本身不能保证输出多样。正式学习块应补充可枚举标签，并在批量生成时做覆盖度
检查。

### 文案多样性维度

- 开头类型：商品先行、反问、感叹、对话否定、场景切入、结果先行；
- 句式节奏：短句连发、重复、停顿、长短句交替、突然转折；
- 消费需求：正餐、解馋、下午茶、通勤、分享、追剧；
- 商品动作：吃、喝、夹、蘸、撕、嗦，且必须符合品类；
- 情绪方向：惊喜、嘴馋、轻吐槽、分享欲、犹豫后真香；
- 信息顺序：商品、场景、体验或疑问先行。

### 人物多样性维度

- 脸型与眉眼组合；
- 五官可见特征和年轻审美方向；
- 发型、长度、刘海和发色；
- 通勤、休闲、甜酷、简约和轻运动服装组合；
- 上下装颜色关系；
- 背景方向，但始终服从固定口播首帧与商品摆放约束。

同批不仅要检查 `source_block_id`、`identity_key` 和 `outfit_key` 不重复，还应对开头类型、人物
身份标签和服装标签的集中度给出预警。相似度只作预警，不能代替 Codex 和人工判断。

## 分阶段实施

### Phase A：每日视频 ASR 文案学习

- 新增文案候选领域模型和 `learning-transcribe`；
- 支持每日目录批量识别、候选列表、编辑稿保存和文案状态转换；
- 原始输入不可变，所有写入原子化；
- 单项失败不终止整个批次。

验收：视频能生成可追溯文案候选；运行命令不会创建或修改任何人物 Prompt 文件。

### Phase B：文案学习审核工作台

- 在现有审核台增加“切换到学习审核/返回任务审核”按钮；
- 原任务审核保持只读；
- 首先支持视频文案的对照修改、revision 冲突保护、保存和提交学习；
- 视频文案候选列表与详情提供可恢复删除入口；删除带 `expected_revision`，只允许尚未批准或
  发布的候选，完整目录移动到 trash，源媒体恢复未识别后可重新转写为新候选；
- 品类族、消费需求和季节限制使用中文下拉，来源块用途使用带解释的受控多选；提交学习前必须
  完成品类族、消费需求和至少一个来源用途并先保存；宽屏分类区压缩为多列；
- 增加安全受限的学习候选 API。

验收：用户能在工作台对照原文修改识别稿；刷新或切换工作台不会丢失已保存内容；不能通过
API 写出 `learning/` 根目录。

### Phase C：按需人物 Prompt 学习

- 新增独立人物 Prompt 候选模型和 `learning-add-person-prompt`；
- 只接受用户主动输入，不建立每日扫描或自动任务；
- 在学习审核台增加独立的“人物 Prompt”页面和“新增人物 Prompt”入口；
- 支持编辑、结构化拆解、相似度预警、保存和提交学习；
- 确保整个流程不读取视频候选，也不调用 ASR。

验收：只有主动输入才会创建人物候选；人物 Prompt 操作不会启动视频识别或改变文案候选状态。

### Phase D：分别发布正式资源

- 将批准文案转换为强类型原文块；
- 将批准人物 Prompt 拆成身份、发型、服装和场景块；
- 增加重复检测、合约校验和发布审计；
- 更新模板版本、Skill、schema、文档和回归测试；
- 发布失败时不修改任何正式资源。

验收：未批准候选不能发布；旧促销和未经确认事实不能进入文案块；人物样本不能覆盖固定画面
约束；正式块可被后续生成安全使用。

### Phase E：多样性调度

- 为两类正式块补充多样性标签；
- 批量生成时分散文案结构、人物身份和服装组合；
- 使用脱敏 golden cases 对比学习前后的重复率和覆盖度；
- 保留现有文案合规、人物年轻审美和批次唯一性校验。

验收：同批文案的开头、节奏和消费情境有明显差异，人物脸型、发型、审美和服装组合也有可
观察差异，且不以虚构事实或破坏固定约束换取多样性。

## 最终建议

在现有 Prompt Engineering CLI 中分别增加“每日视频 ASR 文案学习”和“按需人物 Prompt
学习”是合理的，不需要新增独立业务 CLI。前者是可以每天批量运行的视频转写流程；后者只在
用户主动提供人物 Prompt 时运行。两者不互相触发，也不属于同一个每日批次。

两类内容可以复用审计基础设施和可视化审核台外壳，但必须使用独立命令、状态记录、schema、
目录、校验器和正式资源。

可视化审核台保留原任务审核工作台，并通过顶部单一按钮切换到可写的学习审核工作台。原始输入
永远只读，所有修改写入独立编辑版本；只有人工批准并通过发布校验的内容才能影响后续生成。
