# Prompt Engineering CSV 接入 Dreamina Canvas CLI 深化研究

日期：2026-09-09  
研究对象：`prompt-engineering` 当前 Oceanengine CSV、上游任务 JSON 与 `dreamina-canvas` CLI 1.0.0  
研究边界：只读能力发现、契约核对与本地 `--dry-run`；未创建画布、未保存线上节点、未报价、未生成、未消耗积分。

## 1. 执行摘要

结论不能只用“够”或“不够”概括，需要按目标层级区分：

| 目标 | 现有 CSV 是否足够 | 判断 |
| --- | --- | --- |
| 创建空画布 | 足够，但 CSV 实际不是必需项 | `canvas create` 只要求画布名；CSV 本身没有直接导入入口 |
| 在画布中创建静态图片节点草稿 | 基本足够 | `person_prompt` 可作图片 Prompt，`aspect_ratio` 可作比例；模型、mode、分辨率由接口配置补齐 |
| 创建 TTS 音频节点草稿 | 内容足够，音色不足 | `script` 在当前 TTS 300 字上限内；CSV 的 `明朗女声` 不在实时音色目录中 |
| 创建图片 + 音频 + 视频的节点图草稿 | 部分足够 | 缺视频 Prompt、视频模型/mode/分辨率/时长策略和稳定节点身份 |
| 直接运行数字人口播视频 | 不足 | 当前目录没有名为数字人、口型、audio2video 或 OmniHuman 的模型；多模态模型虽接受图片和音频，但口型驱动效果未经实测 |
| 可恢复、可批量、可审计地运行 | 不足 | CSV 没有画布、Node ID、update ID、submit ID、operation reference、选中 Resource ID 等状态 |

因此，现有 Oceanengine CSV 可以继续保留为原下游格式，但不应直接承担 Dreamina 执行契约。更稳妥的方案是：以 Prompt Engineering 的上游任务 JSON 为语义源，新增独立的 `dreamina_canvas_package` 输出适配器，生成逐条数据、接口配置和人审计划；另由执行器创建画布和节点。

本次已按“不动原配置”的原则新增独立配置 `configs/interfaces/dreamina-canvas.json`。该配置固定使用实时目录中的精确音色 `明媚女声`，把 `1.2x` 记录为强制目标，并要求在图片、音频引用选定后单独写入视频 Prompt；视频 Prompt 必须包含原句 `不包含任何字幕`。

## 2. 核验基线

### 2.1 Dreamina 当前环境

- CLI 版本：`1.0.0`
- commit：`ae2c968`
- edition：`public`
- distribution / region：`cn`
- 当前 `default` profile：已登录
- 当前账号会员：`ultra`
- 实时音色目录：142 个名称

登录态依赖本机凭据访问；在沙箱内读取会显示未登录，在允许访问本机凭据后可正确识别。集成测试不能只在受限沙箱里断言账号未登录。

### 2.2 Prompt Engineering 当前 Oceanengine CSV

固定列为：

```csv
task_id,person_prompt,script,aspect_ratio,voice,title,notes,reference_image_uri,reference_image_url,reference_image_pid
```

职责边界：

- `person_prompt` 是静态首帧图片 Prompt，不是完整视频 Prompt；
- `script` 是去除 `[[NO_SPLIT]]` 标签后的纯口播；
- `voice` 当前是 Oceanengine 语义值 `明朗女声`；
- 三个 `reference_image_*` 字段属于 Oceanengine 素材契约；
- CSV 不保留完整 `avatar_prompt`、批次 `task_name`、`category`、人物去重键和文案来源审计字段。

### 2.3 上游任务 JSON 比 CSV 信息更完整

`generated-task-batch.schema.json` 已经保留：

- 批次级 `task_name`、`category`；
- `marked_script`；
- 完整 `avatar_prompt`；
- 静态 `person_prompt` / 可选 `image_prompt`；
- `identity_key`、`outfit_key`；
- `voice`、LibTV 专用 `voice_label` / `voice_id`；
- 三个参考图字段；
- 文案模式、来源块和审计字段。

Dreamina 适配应从该 JSON 派生，而不是把已经降维的 Oceanengine CSV 当作唯一事实源。

## 3. 实时 Dreamina 能力

### 3.1 图片模型

当前图片目录包含 `seedream_4.0`、`seedream_4.1`、`seedream_4.5`、`seedream_4.6`、`seedream_4.7`、`seedream_5.0_lite`、`seedream_5.0_pro`。

共同事实：

- 都支持 `9:16`；
- Prompt 上限为 2000 字符；
- 支持 `t2i` 和 `i2i`；
- `i2i` 至少需要 1 张图片；
- 单次数量上限为 4 或 8，取决于模型；
- `seedream_4.6` / `4.7` 支持 `1K`、`2K`、`4K`；
- `seedream_5.0_pro` 支持 `1.5K`、`2K`、`4K`，当前各档均列为会员档位；
- 会员规格只表示模型/分辨率要求，最终能否保存和运行仍由服务端裁决。

用于首帧基线时，`seedream_4.6` 或 `seedream_4.7` 的 `9:16 + 1K/2K + count=1` 与现有需求最接近。模型值必须在执行前重新查询，不能把别名 `4.6` 或 `4.7` 当作 `--model`。

#### 图片引用契约存在一处需要保守处理的不一致

实时 `model` 规格对部分模型的 `t2i` 显示可选图片材料，但当前 `identity-and-references.md` 又明确写明图片素材应走 `i2i`，并给出 `t2i accepts only Text canvas references` 的拒绝诊断。按照 CLI Skill 的冲突处理原则，在未做线上无运行保存验证前，不应依赖 `t2i + 图片引用`。

安全路径：

- 无商品参考图：`t2i`；
- 有商品参考图：上传/导入图片后使用 `i2i`；
- 执行器对该分支保留契约版本和验证记录。

### 3.2 TTS 音频

当前 TTS 模型为 `legacy_tts`：

- CLI 公开模式：`tts`；
- 使用 `--prompt` 传入口播正文；
- Prompt 必填，长度 1–300；
- 必须通过 `--voice-name` 传实时目录中的完整音色名；
- TTS 禁止传 `--model`；
- 当前公开参数没有语速、音量、音高设置。

现有 80–100 字口播在 300 字限制内，文本字段本身足够。

但实时 142 个音色中没有 `明朗女声`。存在 `明媚女声`、`纯净女声`、`灵动女声`、`活泼女声`、`流畅女声`、`Vlog配音`、`真人播客女` 等候选，但名称接近不等于声音一致，不能自动把 `明朗女声` 映射成其中任意一个。本次用户已明确选择 Dreamina 使用 `明媚女声`，因此新配置可以固定该精确值；原 Oceanengine 配置中的 `明朗女声` 保持不变。

Dreamina 新配置采用：

- `dreamina_voice_name`：固定为实时 `voice list` 返回的精确值 `明媚女声`；
- `speech_speed`：目标值固定为 `1.2`；
- `speech_speed_enforcement`：当前标记为 `unsupported_by_dreamina_cli_1.0.0`；
- `on_unsupported_speech_speed`：设为 `stop_before_audio_run`，防止配置看似要求 1.2x、实际却静默生成 1.0x；
- 后续不能捏造当前不存在的 `--speed` 参数。只有 Dreamina CLI 正式增加语速控制，或另有经用户授权且可审计的音频变速实现后，才能把 1.2x 标记为已执行。

### 3.3 视频模型

当前目录中没有名称或别名匹配以下关键词的模型：

```text
数字人
口型
audio2video
OmniHuman
```

因此不能仅根据名称确认存在专用数字人口播模型。

当前与“图片 + 音频”结构最接近的候选是多模态 `m2v`：

| 模型 | 9:16 | 时长 | 分辨率 | m2v 音频 | 约束 |
| --- | --- | --- | --- | --- | --- |
| `seedance_2.5` | 支持 | 4–30 秒 | 480p/720p/1080p | 0–10 条，单条和总量上限约 30.2 秒 | 至少有图片、视频或音频之一 |
| `minimax_h3` | 支持 | 4–15 秒 | 768P/2K | 0–3 条，单条和总量上限 15 秒 | 至少有图片或视频，音频只能作为附加输入 |
| `seedance_2.0_*` | 支持 | 4–15 秒 | 720p，部分支持更高 | 可作为 m2v 材料 | 15 秒上限较紧 |
| `wan_3.0` | 支持 | 4–15 秒 | 720P/1080P | 可作为 m2v 材料 | 至少有图片或视频 |
| `seedance_pro_fast` | 支持 | 5–10 秒 | 720p/1080p | 无公开 m2v | 不适合完整 80–100 字口播 |

从纯结构看，`seedance_2.5 + m2v + image node + audio node + 9:16 + 720p` 是首个应测试的候选，因为它允许最长 30 秒并明确接受音频材料。

但必须区分两件事：

1. 模型规格允许图片和音频作为材料；
2. 模型能稳定用音频驱动人物口型并保持首帧身份。

实时规格只能证明第 1 点，不能证明第 2 点。数字人口播适配在没有一条真实样片前只能标记为“结构可行、语义效果待验证”。任何样片运行都可能消耗积分，必须另行报价并由用户批准。

### 3.4 时长是当前最大的执行缺口

现有 CSV 没有目标时长，Dreamina 视频节点又要求显式 `--duration`。同时：

- TTS 不接受语速控制；
- `resource get` 不返回媒体时长；
- operation 结果的资源字段不返回媒体时长；
- node 的资源视图不返回媒体时长；
- 当前 `resource download` 文档化为图片下载，不可依赖它下载音频后测量。

所以，当前公开 CLI 契约无法在 TTS 完成后权威读取音频真实时长。仅凭 80–100 字估算秒数不能作为稳定批量执行依据。

建议 Dreamina CLI 后续至少提供一种能力：

- `resource get` 返回 `durationMs`；或
- `node show` 的资源元信息返回 `durationMs`；或
- `resource download` 正式支持音频，以便执行器用媒体工具读取真实时长。

在该能力补齐前，只能进行单条受控实验：选一条口播，生成 TTS，尝试 30 秒以内的 `seedance_2.5`，人工检查是否截断、留白、口型漂移或忽略音频；不能直接把整批定义为可运行。

## 4. 字段映射矩阵

| Prompt Engineering 字段 | Dreamina 用途 | 充分性 | 处理规则 |
| --- | --- | --- | --- |
| `task_id` | 节点业务键、标题前缀 | 足够 | 不能当 Node ID；Node ID 由 Dreamina 返回并持久化 |
| `title` | 人审标题、节点标题 | 足够 | 节点标题上限 512 UTF-16 code units |
| `notes` | 报告与审计 | 足够 | Dreamina 节点没有直接 notes 字段，不应硬塞进 Prompt |
| `person_prompt` | 图片节点 Prompt | 足够 | 无参考图走 `t2i`；有参考图保守走 `i2i` |
| `script` | TTS `--prompt` | 足够 | 必须保持纯口播，不含 `NO_SPLIT` 标签，且不超过 300 字符 |
| `aspect_ratio` | 图片/视频 `--ratio` | 足够 | 当前 `9:16`、`16:9`、`1:1` 均有可用模型支持；执行前复检 |
| `voice` | 音色意图 | 不足 | `明朗女声` 不在目录；不能原样传给 `--voice-name` |
| `reference_image_uri` | Oceanengine 素材 URI | 不可直接用 | Dreamina 的 `uri:` 当前为预留值，服务端不解析 |
| `reference_image_url` | 图片上传来源 | 条件可用 | 只可作为 `resource upload --source-url` 的临时输入；不要写进 job state |
| `reference_image_pid` | Oceanengine PID | 不可用 | Dreamina 没有对应公开字段 |
| 上游 `avatar_prompt` | 视频节点 Prompt | 适合，但 CSV 丢失 | 应从任务 JSON 进入 Dreamina 包；选择图片和音频后重新组装，并强制包含 `不包含任何字幕` |
| 上游 `image_prompt` | 图片节点 Prompt | 适合 | 缺省时可复用 `person_prompt` |
| 上游 `voice_label` / `voice_id` | LibTV 音色 | 不可直接用 | Dreamina 只接受实时 `voiceName` |

## 5. 现有测试 CSV 的实际状况

仓库内目前可见两份历史测试 CSV，共 10 行：

- `tests/cases/watermelon_batch_20260702.csv`
- `tests/cases/honey_peach_batch_20260702.csv`

观察结果：

- 10 列均符合 Oceanengine CSV 旧契约；
- 每行 `task_id`、`person_prompt`、`script`、`aspect_ratio`、`voice`、`title`、`notes` 非空；
- 三个参考图字段全部为空；
- `aspect_ratio` 全部为 `9:16`；
- `voice` 全部为 `明朗女声`；
- `script` 长度约 81–86 字符，可进入当前 TTS；
- `person_prompt` 长度约 247–272 字符，且没有把 `竖屏9:16，固定中景，手机实拍` 前置。

这些历史 fixture 会触发当前 Prompt Engineering 的视觉 Prompt 校验：当前要求 120–180 字符，并在开头前置固定镜头风格。Dreamina 图片模型本身允许到 2000 字符，所以平台可能接受这些旧 Prompt，但它们已经不代表当前上游质量契约。建议把它们标注为历史 fixture，或用当前规则重新生成测试数据，避免集成测试出现“Dreamina 能收、Prompt Engineering 自己不认可”的双重标准。

## 6. 推荐架构

### 6.1 不改现有 Oceanengine CSV

现有 CSV 已有稳定消费者，直接增加 Dreamina 专属列会扩大兼容风险。推荐沿用已有 LibTV 适配器的三件套模式，新增：

```text
<task>.dreamina.csv
<task>.dreamina.interface.json
<task>.dreamina.plan.md
```

职责分离：

- CSV：只保存每条任务会变化的内容；
- interface JSON：保存模型选择、节点模板、参数、能力发现时间和执行边界；
- plan Markdown：给人工审核内容、映射和风险；
- job state：只由执行器在真实创建/运行时产生，不属于 Prompt Engineering 内容包。

### 6.2 推荐逐条 CSV 字段

```csv
task_id,title,notes,image_prompt,audio_prompt,video_prompt,aspect_ratio,voice_intent,dreamina_voice_name,reference_image_key
```

说明：

- `image_prompt`：复用上游 `image_prompt`，无值时复用 `person_prompt`；
- `audio_prompt`：由 `marked_script` 去标签后生成；
- `video_prompt`：不能只复用静态图片 Prompt；应从上游 `avatar_prompt` 与 Dreamina 约束重新组装，任务包保留 `{image_node_id}` 占位符，选择图片、音频后替换为真实图片 Node ID；要求完整逐字使用音频节点内容，不得省略、改写、截断或提前结束，并强制包含原句 `不包含任何字幕`；Dreamina 视频阶段允许人物触碰商品、切镜和运镜，适配器需移除上游带入的对应禁止语句；
- `voice_intent`：保留业务语义；
- `dreamina_voice_name`：必须由实时目录确认；
- `reference_image_key`：只引用包外稳定资产登记，不复制 signed URL。

### 6.3 推荐接口配置

仓库新增的独立配置为 `configs/interfaces/dreamina-canvas.json`。它不修改 `configs/projects/`、`configs/validation/` 或 LibTV 配置。核心结构如下，具体模型值在执行时仍须通过当前 CLI schema 校验：

```json
{
  "schema_version": "dreamina-interface-config/v1",
  "interface": "dreamina_canvas",
  "catalog_observed_at": "2026-09-09T00:00:00+08:00",
  "discovery_required_before_execution": true,
  "defaults": {
    "dreamina_voice_name": "明媚女声",
    "speech_speed": 1.2,
    "required_video_prompt_phrases": ["不包含任何字幕"]
  },
  "canvas": {
    "name_template": "{task_name}-{date}",
    "one_canvas_per_batch": true
  },
  "nodes": {
    "image": {
      "name_template": "{task_id}-image",
      "model": "seedream_4.6",
      "mode_without_reference": "t2i",
      "mode_with_reference": "i2i",
      "resolution": "1K",
      "count": 1,
      "prompt_field": "image_prompt"
    },
    "audio": {
      "name_template": "{task_id}-audio",
      "mode": "tts",
      "prompt_field": "audio_prompt",
      "voice_name": "明媚女声",
      "speech_speed": 1.2,
      "speech_speed_enforcement": "unsupported_by_dreamina_cli_1.0.0",
      "on_unsupported_speech_speed": "stop_before_audio_run"
    },
    "video": {
      "name_template": "{task_id}-video",
      "model": "seedance_2.5",
      "mode": "m2v",
      "resolution": "720p",
      "ratio_field": "aspect_ratio",
      "duration_policy": "requires_verified_audio_duration",
      "prompt_field": "video_prompt",
      "prompt_write_timing": "after_image_and_audio_references_selected",
      "prompt_template": "让{{node:{image_node_id}}}中的人物保持首帧身份与服装，{avatar_prompt}。必须完整使用所选音频节点的全部内容进行口播，逐字说完，不得省略、改写、截断或提前结束，口型与音频同步，身体动作自然，不包含任何字幕。",
      "required_prompt_phrases": ["必须完整使用所选音频节点的全部内容进行口播", "逐字说完", "不得省略、改写、截断或提前结束", "不包含任何字幕"],
      "inputs": ["image", "audio"],
      "count": 1
    }
  },
  "execution_boundary": {
    "create_canvas": false,
    "create_nodes": false,
    "run_nodes": false,
    "requires_user_confirmation_for_paid_generation": true
  }
}
```

该配置中的模型只是本次实时目录下的首测候选，不是永久默认。执行器每次都应重新运行 `schema`、`model list/find` 和 `voice list`，确认 canonical model、flag 和音色仍有效。`speech_speed: 1.2` 是需求目标，不是当前 CLI 可直接下发的参数；执行器不得捏造 `--speed`，也不得在未达到 1.2x 时宣称已满足配置。

## 7. 最小节点图

对每一行，最小充分图为：

```text
image_prompt ──> 图片节点 ──┐
                            ├──> m2v 视频节点
audio_prompt ──> TTS 节点 ─┘
```

不需要默认创建 Element、Text 或 timeline：

- 同一人物需要跨多条成片复用时，才考虑 Element；
- 多片段合成时，才考虑 timeline；
- 需要在画布内展示文案审计时，才考虑 Text；
- 当前 Prompt Engineering 规则反而要求每条使用不同人物，不应为了“统一”默认创建共享人物 Element。

在画布已有来源节点时，下游视频应引用 Node ID，而不是提取 Resource ID：

```text
--ref node:<image-node-id>
--ref node:<audio-node-id>
```

视频 Prompt 中可以用 `{{node:<image-node-id>}}` 明确绑定人物图片；音频只放在引用列表即可。保存后必须回读 `generation.references[]` 与 `upstreamNodeIds`，确认两条连线真实存在。

选择图片和音频之后，应重新写入视频节点 Prompt，而不是沿用图片节点 Prompt。推荐模板为：

```text
让{{node:<image-node-id>}}中的人物保持首帧身份与服装，<avatar_prompt>。必须完整使用所选音频节点的全部内容进行口播，逐字说完，不得省略、改写、截断或提前结束，口型与音频同步，身体动作自然，不包含任何字幕。
```

其中图片节点必须通过 `--ref node:<image-node-id>` 建立引用，同时在 Prompt 中使用真实 `{{node:<image-node-id>}}` 占位符强化人物绑定；音频节点通过 `--ref node:<audio-node-id>` 建立引用。提交前必须确认两条引用均存在，并对最终 Prompt 做精确短语校验：必须包含完整音频、逐字说完、不得省略改写截断或提前结束，以及 `不包含任何字幕`。Dreamina 专用适配层会移除“不接触/不触碰商品”、固定机位、不切镜、一镜到底、不运镜和不推拉摇移等限制；静态首帧和其他平台规则保持不变。

## 8. 执行阶段与授权边界

建议拆成四个独立层级：

1. 生成 Prompt Engineering 内容和任务包；
2. 创建画布并保存节点草稿；
3. 对图片/TTS 节点报价、用户批准后生成；
4. 确认上游资源和时长后，对视频节点报价、用户批准后生成。

任务包输出不应自动创建画布；创建画布不应自动运行节点；图片/TTS 获批不代表视频获批。

真实运行时必须持久化：

```json
{
  "jobKey": "...",
  "projectId": "...",
  "items": {
    "task-id": {
      "imageNodeId": "...",
      "imageSubmitId": "...",
      "audioNodeId": "...",
      "audioSubmitId": "...",
      "videoNodeId": "...",
      "videoSubmitId": "...",
      "selectedResourceIds": {}
    }
  }
}
```

job state 不得保存 access token、signed URL、provider payload 或 credit confirmation token。批量运行时每个节点必须有独立 submit ID；响应丢失后先用同一 submit ID 只读恢复，不能换新 ID 盲目重提。

## 9. 本地语法验证

本次用 `--dry-run` 验证了以下结构在 CLI 1.0.0 的本地参数层可成立：

- 图片：`seedream_4.6 + t2i + 9:16 + 1K + count=1`；
- TTS：`tts + 明媚女声 + script`；
- 视频：`seedance_2.5 + m2v + 9:16 + 720p + 15s + image/audio Node 引用`。

`--dry-run` 明确没有网络、草稿、报价、批准、运行和积分副作用。它只证明命令结构可表达，不能证明：

- 项目与节点权限；
- 引用资源已就绪；
- 服务端最终准入；
- 数字人口型同步效果；
- 音频与视频时长匹配。

## 10. 预检规则建议

Dreamina 适配器在任何线上写入前应检查：

1. CSV/JSON 编码与必填字段；
2. `task_id` 唯一且只含允许字符；
3. `image_prompt` 通过 Prompt Engineering 当前视觉校验；
4. `audio_prompt` 不含 `NO_SPLIT`，且不超过实时 TTS 上限；
5. `aspect_ratio` 被选定图片和视频模型共同支持；
6. `dreamina_voice_name` 等于 `明媚女声`，且精确存在于完整分页音色目录；
7. 模型使用 canonical 值，不使用 alias；
8. 有参考图时已转换为可用图片 Resource 或节点；
9. `reference_image_uri` / PID 不被误当成 Dreamina 引用；
10. 视频 Prompt 在图片和音频引用选定后重新生成，且不是静态 `person_prompt` 的简单复制；
11. 最终视频 Prompt 精确包含 `不包含任何字幕`；
12. 目标语速为 1.2x；当前 CLI 无法执行时，在音频运行前停止；
13. 音频时长可验证且不超过模型上限；
14. 运行前已生成并保存恢复所需身份；
15. 报价超出用户批准上限时停止；
16. 每个结果进入终态且存在可用 Resource 后才算完成。

## 11. 最小验证矩阵

| 用例 | 目标 | 是否消耗积分 |
| --- | --- | --- |
| 旧 CSV 静态检查 | 验证字段、旧 fixture 漂移和音色不匹配 | 否 |
| 新任务 JSON → Dreamina 包 | 验证字段不丢失、三件套拒绝覆盖 | 否 |
| Dreamina CLI dry-run | 验证命令结构、mode 和引用格式 | 否 |
| 创建一块测试画布并只保存 3 个节点 | 验证真实节点图和上游连线 | 否，但会写线上草稿 |
| 单条图片生成 | 验证首帧人物、商品和构图 | 是，需报价批准 |
| 单条 TTS 生成 | 验证音色、字数与真实时长 | 是，需报价批准 |
| 单条 m2v 生成 | 验证是否真正使用图片和音频、口型同步、固定镜头 | 是，需报价批准 |
| 中断恢复 | 验证同一 submit ID 恢复，不重复扣费 | 可能，必须复用原任务 |
| 批量 3 条 | 验证人物差异、节点隔离、恢复向量和预算 | 是，单条通过后再做 |

首个付费验收不应直接跑整批。建议先选 1 行，并明确验收：人物身份是否来自首帧图、商品是否完整、口型是否跟随音频、是否逐字覆盖音频全部内容且没有少话、输出是否为 9:16；切镜和运镜允许自然发生。

## 12. 最终判断

现有 CSV 的内容层信息并不差：它已经有静态人物图、纯口播、比例、标题和任务键，足以成为 Dreamina 首帧与 TTS 的输入来源。真正不足的是“平台执行契约”。

最重要的改造不是往旧 CSV 里继续加列，而是：

1. 以现有任务 JSON 作为 Dreamina 语义源，保留 `avatar_prompt`；
2. 新增独立 Dreamina 三件套适配器；
3. 增加精确 `dreamina_voice_name`，不要复用 `明朗女声` 或 LibTV voice ID；
4. Dreamina 新配置固定 `明媚女声`，并把 1.2x 作为必须满足但当前尚不可执行的语速目标；
5. 视频 Prompt 在图片和音频引用选定后重新写入，并强制包含 `不包含任何字幕`；
6. 运行时实时发现模型和音色；
7. 先验证音频真实时长能力，再开放批量视频；
8. 用一条付费样片验证 `seedance_2.5 m2v` 是否真的能承担数字人口播；
9. 将画布创建、节点保存、媒体生成和视频生成保持为不同授权层。

在完成第 5、6 点前，可以把集成定义为“可创建 Dreamina 内容画布草稿”，不能定义为“已跑通 Dreamina 数字人口播生产链路”。

## 13. 实现状态

已在 Prompt Engineering CLI 中增加 `dreamina_canvas_package` 输出格式。通过
`avatar-prompts package --format dreamina_canvas_package` 可在既有日期/任务目录下生成：

```text
<task>.dreamina.csv
<task>.dreamina.interface.json
<task>.dreamina.plan.md
```

实现保持原 Oceanengine CSV 和 LibTV 三件套不变。Dreamina CSV 从上游任务 JSON 读取
`image_prompt`、纯口播和完整 `avatar_prompt`，确定性生成新的 `video_prompt`；任务包保留
`{image_node_id}`，`save-dreamina-video-node` 会用真实图片 Node ID 替换它，同时把图片、音频
Node ID 都作为 `--ref` 传给官方 CLI。该 Prompt 要求逐字使用音频节点全部内容，不得少话，
默认允许切镜和运镜，并保证精确包含 `不包含任何字幕`。接口配置固定音色
`明媚女声`，记录 1.2x 目标和当前 CLI 不支持语速时的阻断策略。整个打包流程只写本地文件，
不会创建画布、节点或提交付费生成。

## 14. 参考文件

- `prompt-engineering/SKILL.md`
- `prompt-engineering/references/generated-task-batch.schema.json`
- `prompt-engineering/references/oceanengine-contract.md`
- `prompt-engineering/references/runtime.md`
- `src/avatar_prompt_pipeline/artifacts.py`
- `src/avatar_prompt_pipeline/batch.py`
- `src/avatar_prompt_pipeline/validation.py`
- `docs/feasibility-study.md`
- `docs/libtv-omnihuman-workflow-notes.md`
- `configs/interfaces/dreamina-canvas.json`
- `/Users/sakana/.agents/skills/dreamina-canvas-cli/SKILL.md`
- `/Users/sakana/.agents/skills/dreamina-canvas-cli/references/identity-and-references.md`
- `/Users/sakana/.agents/skills/dreamina-canvas-cli/references/credits-and-hitl.md`
- `/Users/sakana/.agents/skills/dreamina-canvas-cli/references/recovery-and-idempotency.md`
- `/Users/sakana/.agents/skills/dreamina-canvas-cli/references/completion-and-validation.md`
