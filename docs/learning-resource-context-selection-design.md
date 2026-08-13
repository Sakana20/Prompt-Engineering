# 学习资源按需筛选与上下文预算方案

## 背景

正式学习资源需要完整保存，便于审计、回滚和后续重新筛选；但生成时不应把整份学习库全部
放进 Codex 上下文。

方案制定时存在两个不同程度的问题：

- 人物资源 `person-prompt-source-blocks.md` 已有 76 个块、约 3.6 万字符，
  `compose_prompt_package(...)` 和 `render_avatar_prompt(...)` 会把全文追加到人物 Prompt；
- 文案资源 `volume-copy-source-blocks.md` 当前只有 13 个固化原文块，网页发布区尚为空，短期
  消耗较小；但网页发布块增长后，当前实现仍会把整个发布区追加到文案 Prompt。

此外，Skill 当前要求 Codex在生成前读取完整正式资源。即使只优化 Python 拼装，如果不同时
调整 Skill 工作流，Codex仍可能主动读取全文件，因此必须同时治理 CLI 注入和 Skill 读取两条
上下文入口。

## 目标

1. 正式学习资源继续完整、可审计地落盘，不删除历史块，不改变已发布候选状态。
2. 生成时只提供与当前任务相关的少量候选块，不再全文注入人物库或网页文案发布区。
3. Python 只做确定性解析、硬过滤、排序和压缩；最终语义选择仍由 Codex完成。
4. 不把发布清单 JSON、候选 ID 或审计记录写入正式文案正文。
5. 保留现有原文块格式、block ID、批次比例、来源登记、风险边界和旧任务清单兼容性。
6. 每次生成都能说明实际选择了哪些块，并量化注入字符数，便于观察额度变化。

## 非目标

- 不接入向量数据库、Embedding、其他 LLM 或远程检索服务；
- 不让 Python 根据自然语言自动创作文案或人物描述；
- 不改变 `pending → approved → published` 的审核发布状态机；
- 不把完整学习库拆成大量零散文件；
- 不用压缩学习内容为理由绕过固定画面、事实边界或批次唯一性校验。

## 核心原则

### 正式资源与生成上下文分离

正式资源是完整事实来源，生成上下文只是本次任务的临时投影：

```text
完整正式 Markdown 资源
  → 确定性解析
  → 硬条件过滤
  → 稳定排序与数量/字符预算
  → 紧凑候选上下文
  → Codex 语义选择与生成
  → 现有确定性校验
```

筛选结果不得反向覆盖正式资源。未入选只表示本次未使用，不表示删除、驳回或降级。

### 正式资源保持权威

- 文案正式库继续使用 `### block-id` 加 fenced `text` 的现有格式；
- 人物正式库继续保存 identity、hair、outfit、scene 块；
- `learning/<kind>/published/provenance.jsonl` 继续只承担本地审计，不进入生成 Prompt；
- 如需紧凑索引，应使用可从正式资源重建的派生 Markdown 目录，不能成为第二份权威学习库，
  也不能用来替代正式资源一致性检查。

## 选择上下文

### 文案选择输入

- 品类与品类族；
- 消费需求；
- 当前季节；
- `copy_mode`；
- 批次数量；
- 已确认商品事实是否足以填写强类型插槽；
- 当前批次已经使用的 `source_block_id`。

### 人物选择输入

- 口播对应的生活场景；
- 当前季节；
- 批次数量；
- 账号固定人物边界；
- 当前批次已使用的 `identity_key`、`outfit_key` 和学习块 ID；
- identity、hair、outfit、scene 四类覆盖需求。

不得把平台、红包、价格、销量或未经确认功效用作人物块筛选依据。

## 确定性筛选边界

### 文案块

Python 可以执行：

1. 排除品类族不兼容块，例如饮品排除固体食品直填块；
2. `source_fill` 排除季节冲突块；
3. 排除插槽数量超过当前已确认事实数量的块；
4. 在同一 `copy_mode` 内排除已经使用的 block ID；
5. 优先匹配受控的消费需求和来源用途；
6. 使用 block ID 作为最终稳定排序键，保证相同输入得到相同候选集。

Python 不得判断“哪段文案更自然”或改写模板。候选集中具体选哪一块、如何进行
`human_rewrite`，仍由 Codex决定。

### 人物块

Python 可以执行：

1. 只接受 identity、hair、outfit、scene 四类已发布块；
2. 排除命中 `incompatible_with`、固定禁用方向或季节冲突的块；
3. 按 `compatible_with` 与受控场景/季节标签的交集排序；
4. 优先补齐当前候选集中缺失的 block type；
5. 降低本批次已使用块和集中度过高标签的优先级；
6. 使用 block type、匹配分数和 block ID 做稳定排序。

Python 不得复刻具体真人，也不得自行补写人物语义。Codex只在筛选后的候选中做兼容组合，
并继续受人物固定规则约束。

## 紧凑投影

人物正式块中的以下字段不需要每次都注入：

- `source_candidate_id`；
- 重复的来源候选说明；
- 已由发布校验和固定人物规则覆盖的 `removed_constraints`；
- 空的 `removed_risks`。

人物候选上下文只保留：

```text
block_id | block_type | description | compatible_with | incompatible_with | diversity_tags
```

文案候选上下文只保留：

```text
block_id | 适配摘要 | 原始 text 模板
```

紧凑投影只存在于命令输出或 PromptPackage 中，不回写正式 Markdown。

## 默认预算

预算以字符数和块数量为确定性门禁，不依赖某个模型的 tokenizer：

| 资源 | 单条任务默认值 | 批量任务默认值 | 字符硬上限 |
| --- | ---: | ---: | ---: |
| 人物 identity | 2 块 | 最多 4 块 | 与人物总预算合并 |
| 人物 hair | 2 块 | 最多 4 块 | 与人物总预算合并 |
| 人物 outfit | 3 块 | 最多 6 块 | 与人物总预算合并 |
| 人物 scene | 2 块 | 最多 4 块 | 与人物总预算合并 |
| 人物总上下文 | — | — | 4,500 字符 |
| 文案原文块 | 最多 4 块 | 每种来源模式最多 `max(4, floor(N/2)+2)` 块 | 7,000 字符 |

如果满足硬条件的块超过预算，按稳定排名截断；如果不足，则允许 Codex按现有规则使用
`natural_generate` 或自行设计符合固定人物边界的变量，不能为了凑够数量放入不兼容块。

字符上限是初始工程预算，实施后应记录实际 `selected_character_count` 和生成质量，再根据回归
样本调整。不得仅依据估算 token 数宣称节省比例。

## CLI 与代码接口方案

### 新增领域对象

新增不可变类型，避免传播无结构字典：

```text
LearningContextRequest
  - category
  - consumption_need
  - season
  - batch_size
  - copy_modes
  - used_copy_block_ids
  - used_person_block_ids

SelectedLearningContext
  - copy_blocks
  - person_blocks
  - excluded_counts
  - selected_character_count
  - budget_character_limit
  - truncated
```

人物块和文案块分别使用明确 dataclass。解析失败、未知 block type、重复 block ID 或正式资源
格式错误必须显式失败，不能静默丢弃整个资源。

### 生成入口

1. `compose` 在构建 PromptPackage 前运行选择器；
2. `render_avatar_prompt(...)` 接收显式的已选人物上下文，不再自行读取全文资源；
3. 为没有经过 `compose` 的 Codex工作流提供只读 CLI，例如：

```bash
avatar-prompts learning-context \
  --category 咖啡 \
  --consumption-need 通勤 \
  --season summer \
  --batch-size 10
```

4. 命令只输出紧凑候选集和选择审计，不生成文案、不发布候选、不写正式资源；
5. `compose`、`package` 等现有生产命令的 preflight 门禁保持原顺序：先处理 approved 与资源
   一致性，再选择 published 块；
6. `SKILL.md` 改为默认调用选择入口并读取其结果，禁止在正常生成时直接加载完整人物库或完整
   网页文案发布区。只有审计、修复、发布和调试任务才读取完整资源。

### PromptPackage 审计字段

PromptPackage 增加向后兼容的可选字段：

- `selected_copy_block_ids`；
- `selected_person_block_ids`；
- `learning_context_character_count`；
- `learning_context_truncated`。

旧 PromptPackage 不含这些字段时仍可读取。新批次产物继续按现有字段登记实际采用的
`source_block_id`、`identity_key` 和 `outfit_key`；“进入候选集”和“最终采用”必须区分。

## 发布后的索引维护

优先直接解析现有正式 Markdown。若性能或文案元数据不足以支持稳定筛选，再增加一个紧凑的
派生 Markdown 目录，要求：

- 每行只保存 block ID、类型和受控标签；
- 可完全从正式资源及发布清单重建；
- 与正式资源在同一事务中更新；
- preflight 同时校验目录中的 ID 不缺失、不多出；
- 目录损坏时停止生成并要求重建，不回退到全文注入；
- 目录不是正式学习内容，删除后可以确定性重建。

首版不得为了方便直接新增第二份权威 JSON 学习库。

## 分阶段实施

### 阶段 A：人物资源止损

1. 实现人物 Markdown 解析器和紧凑投影；
2. 实现按类型、兼容标签、季节和去重状态筛选；
3. 替换 `service.py` 的人物全文 `_learned_resource_context(...)`；
4. 调整 Skill，正常生成不再读取完整人物资源；
5. 增加上下文字符统计和所选 block ID 审计。

这是最高优先级，因为当前人物资源已经达到 76 个块。

### 阶段 B：网页文案发布区筛选

1. 将文案 Prompt 中的学习块改为选择器输出；
2. 保持原有固化真人原文块和网页发布块的统一 block ID 契约；
3. 根据品类族、消费需求、季节、来源用途、插槽事实和批次去重筛选；
4. 保留 `human_rewrite=floor(N/2)` 和 `source_fill`/`natural_generate` 回退规则；
5. 网页发布区为空时保持当前输出兼容。

### 阶段 C：预算观测与调优

1. 在安全调试输出中记录正式块总数、过滤后数量、最终数量和字符数；
2. 为单条、5 条、10 条任务建立上下文体积与生成质量基线；
3. 检查人物/服装重复率、文案来源覆盖率和校验通过率；
4. 只有质量回归通过后再下调字符预算。

## 测试方案

### 单元测试

- 人物四类块解析、非法 JSON、未知类型和重复 ID；
- 文案 fenced `text` 解析与原格式保持；
- 饮品、固体食品、季节、消费需求和来源用途过滤；
- `incompatible_with` 硬排除；
- 相同输入得到相同顺序；
- 块数量和字符预算截断；
- 紧凑投影不包含 provenance、候选 ID 和冗余安全字段；
- 空资源安全回退。

### 集成测试

- `compose` 的人物模板不再包含完整正式人物文件；
- 发布 100 个人物块后，注入上下文仍不超过预算；
- 发布大量文案块后，只注入与当前品类/季节兼容的候选；
- preflight 未通过时不执行选择和生成；
- 已选 block ID 与 PromptPackage 审计字段一致；
- 已安装 Skill 与仓库行为一致。

### 回归测试

- 现有 181 项测试保持通过；
- 现有原文块格式、旧任务清单和 CSV 输出不变；
- 人物固定中景、直视镜头、商品摆放、不手持、不接触、logo、无字幕校验不变；
- 文案利益点、事实、季节、天气和批次来源校验不变；
- 无 learned 资源时结果保持兼容。

## 验收标准

1. 76 个人物块存在时，单次人物学习上下文不超过 4,500 字符；
2. 生成 Prompt 中不再出现完整 `person-prompt-source-blocks.md`；
3. 文案网页发布区增长后，单次注入不超过 7,000 字符；
4. 每次生成可查看候选 block ID、最终采用 block ID、截断状态和字符数；
5. 不兼容块不会因预算不足被重新放入；
6. 正式 Markdown、候选状态、provenance 和 block ID 不因筛选改变；
7. Ruff、mypy strict、完整 pytest、Skill 校验、本地安装比对和已安装 CLI 验证全部通过。

## 风险与取舍

- 预算过小会降低多样性：优先保留每种类型覆盖和批次所需数量，再压缩冗余字段；
- 标签质量不足会影响召回：首版保留少量稳定后备块，但后备仍必须通过硬过滤；
- 仅按关键词筛选可能漏掉语义相近块：Python 只负责受控标签和硬条件，Codex在小候选集中完成
  语义判断；
- 全文读取更简单但成本会随学习量线性增长，因此不能作为长期回退路径；
- 派生索引会增加一致性维护成本，所以先尝试直接解析正式 Markdown，确认不足后再引入可重建
  的紧凑 Markdown 目录。

## 实施状态

- 人物阶段已完成：76 个历史 block ID 保留，正式库已改为块标题加 fenced `text`；
- `compose` 与人物 Prompt 渲染每次最多注入 10 个块，并按当前季节排除明显冲突块；
- PromptPackage 已登记所选人物 block ID 与学习上下文字符数；
- 文案网页发布区筛选仍待后续实施。

## 推荐决策

先实施阶段 A，立即解决人物全文注入；稳定后实施阶段 B，避免文案网页发布区未来重复出现同一
问题。正式学习资料仍完整保存，CLI/Codex只消费本次需要的紧凑候选集。
