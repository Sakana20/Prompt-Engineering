# LibTV OmniHuman 数字人任务包设计笔记

日期：2026-07-15

本文档沉淀一次从 CSV 输入到 LibTV 生成数字人视频的实际试跑经验。目标是指导后续修改
`prompt-engineering` skill 的输出格式，但本文档本身不改代码、不改 skill。

## 实现基准

后续实现 `libtv_omnihuman_package` 时，以本文档中的字段、默认值和约束为准。若历史试跑
记录、旧 CSV、旧 Oceanengine 口径或模型默认值与本文档冲突，按本文档执行。

当前已明确的默认音色语义：

```text
女声默认：温暖闺蜜
男声默认：温润男声
```

`温暖闺蜜` 已确认 LibTV/TTS `voice_id`：

```text
Chinese (Mandarin)_Warm_Bestie
```

`温润男声` 已确认 LibTV/TTS `voice_id`：

```text
Chinese (Mandarin)_Gentleman
```

## 试跑结论

已用第一条 `jierou-01` 跑通完整 LibTV 链路：

1. 用 `person_prompt` 创建图片节点，生成数字人首帧图。
2. 用 `script` 创建音频节点，生成 TTS 口播音频。
3. 用首帧图节点和音频节点作为上游，创建 `OmniHuman 1.5` 视频节点，生成数字人视频。

试跑画布：

```text
https://www.liblib.tv/canvas?projectId=d0fbc199dcd643b1a74192019a3c746e
```

试跑视频：

```text
https://libtv-res.liblib.art/sd-gen-save-img/genius_playground/video/1af68f6443e94404974952f5bfd87173/4a587094ba17bd8540b76c9730436bc5b4eabc58229084891b27aa4848498084.mp4
```

## 当前 CSV 到 LibTV 的实际转换

原 CSV 字段：

```csv
task_id,person_prompt,script,aspect_ratio,voice,title,notes
```

实际映射：

| CSV 字段 | LibTV 用途 | 说明 |
| --- | --- | --- |
| `task_id` | 节点名前缀 | 例如 `jierou-01-image`、`jierou-01-audio`、`jierou-01-omnihuman-video` |
| `person_prompt` | 图片节点 prompt | 用于生成 OmniHuman 所需参考图片/首帧人物图 |
| `script` | 音频节点 prompt | 用于 TTS 生成口播音频 |
| `aspect_ratio` | 图片比例 | 当前映射为图片节点 `ratio=9:16` |
| `voice` | 音色意图 | 映射为任务包 `voice_label`；女声默认 `温暖闺蜜`，男声默认 `温润男声` |
| `title` | 审阅标题 | 暂不直接写入 LibTV 参数，可用于报告和节点命名 |
| `notes` | 审计备注 | 暂不直接写入 LibTV 参数，可用于批量日志 |

第一条试跑对应节点：

```text
jierou-01-image
  type: image
  model: Z-image Turbo
  prompt: CSV.person_prompt
  ratio: 9:16
  quality: 1K
  target_resolution: 720x1280
  count: 1

jierou-01-audio
  type: audio
  model: Minimax-speech-2.8-turbo
  prompt: CSV.script
  voice_label: 温暖闺蜜
  voice_id: Chinese (Mandarin)_Warm_Bestie
  speed: 1.2
  voicePitch: 0
  vol: 8

jierou-01-omnihuman-video
  type: video
  model: OmniHuman 1.5
  modeType: audio2video
  left inputs:
    - jierou-01-image
    - jierou-01-audio
  ratio: auto
  resolution: auto
  target_resolution: 720x1280
  fastMode: 0
  count: 1
```

## 分辨率约束与 LibTV 支持情况

目标成片规格固定为：

```text
720x1280
```

该规格是**任务包约束与产物验收标准**，不是当前 OmniHuman 节点可以直接写入的
`resolution` 参数。

已核对 `libtv-cli` 与当前模型 schema：

| 层级 | 支持情况 | 结论 |
| --- | --- | --- |
| `libtv-cli` skill | 支持通过 `-s/--set` 写入模型 schema 中声明的 `ratio`、`resolution`、`quality` 等参数 | CLI 能写参数，但不能绕过模型 schema |
| `Z-image Turbo` 图片模型 | 支持 `ratio=9:16`，支持 `quality=1K/2K/4K`；不支持直接填写 `720x1280` | 只能用 `9:16` 约束竖屏比例，用 `quality` 约束清晰度档位 |
| `OmniHuman 1.5` 视频模型 | `ratio` 仅支持 `auto`，`resolution` 仅支持 `auto` | 不能直接指定 `720x1280` 或 `720p` |
| 其他视频模型示例：`Seedance 2.0 VIP` | 支持 `ratio=9:16` 与 `resolution=720p` | 对这类模型可用 `9:16 + 720p` 表达 720 级竖屏，但不是 OmniHuman 当前 schema |

因此，LibTV OmniHuman 任务包应同时保留两类字段：

```text
model parameters:
  image_ratio: 9:16
  image_quality: 1K 或 2K
  video_ratio: auto
  video_resolution: auto

acceptance target:
  target_width: 720
  target_height: 1280
  target_resolution: 720x1280
```

执行器或人工验收阶段必须检查最终视频文件的真实宽高；如果不是 `720x1280`，只能标记为
不合格或进入后处理转码/缩放步骤，不能假设 OmniHuman 已按该尺寸输出。

## 为什么不能直接把现有 CSV 喂给 OmniHuman

`OmniHuman 1.5` 的 schema 显示它是数字人视频模型，但不是直接消费文案 CSV 的模型。它要求同时有：

```text
image
audio
```

因此 `prompt-engineering` 不能只输出 `person_prompt` 和 `script` 就认为 LibTV 可直接跑。它需要产出一个明确的三段式任务包：

```text
person_prompt -> image node -> generated image
script        -> audio node -> generated audio
image+audio   -> video node -> OmniHuman video
```

## 建议新增输出模式

建议在 `prompt-engineering` 中新增输出模式：

```text
libtv_omnihuman_package
```

这个模式不直接提交生成，只生成可审阅、可执行的 LibTV 任务包。原因是 `libtv node --run` 会消耗积分，必须和内容生成分开授权。

建议同时输出三份文件：

```text
<task>.libtv.csv
<task>.libtv.interface.json
<task>.libtv.plan.md
```

其中 CSV 只保存任务行数据，接口配置 JSON 保存 LibTV/OmniHuman 的模型、节点、参数和验收约束，
Markdown 用于人审和单条试跑记录。

## 新增接口配置文件输出

后续实现时，`prompt-engineering` 必须新增一个接口配置文件输出，用于区分不同下游接口。
接口配置文件是任务包的一部分，但它不包含逐条文案正文。

推荐文件名：

```text
<task>.libtv.interface.json
```

设计原则：

- CSV 只表达“这一条任务是什么”，不表达“某个接口怎么跑”；
- 接口配置 JSON 表达“这个任务包要走哪个接口、用哪些模型、节点如何命名、参数默认值是什么”；
- `libtv_omnihuman`、`oceanengine`、未来其它接口必须通过配置文件区分，不能靠 CSV 字段堆叠区分；
- 如果某个接口不支持配置中的精确参数，配置文件必须把它标为验收目标，而不是伪装成模型参数；
- 执行器读取 CSV + interface JSON 后再生成具体命令或下游文件。

推荐结构：

```json
{
  "schema_version": "libtv-interface-config/v1",
  "interface": "libtv_omnihuman",
  "task_package": {
    "csv": "<task>.libtv.csv",
    "plan": "<task>.libtv.plan.md"
  },
  "defaults": {
    "target_width": 720,
    "target_height": 1280,
    "target_resolution": "720x1280",
    "voice_labels": {
      "female": "温暖闺蜜",
      "male": "温润男声"
    },
    "voice_ids": {
      "温暖闺蜜": "Chinese (Mandarin)_Warm_Bestie",
      "温润男声": "Chinese (Mandarin)_Gentleman"
    }
  },
  "nodes": {
    "image": {
      "name_template": "{task_id}-image",
      "type": "image",
      "model": "Z-image Turbo",
      "params": {
        "ratio": "9:16",
        "quality": "1K",
        "count": 1
      },
      "prompt_field": "image_prompt"
    },
    "audio": {
      "name_template": "{task_id}-audio",
      "type": "audio",
      "model": "Minimax-speech-2.8-turbo",
      "params": {
        "speed": 1.2,
        "voicePitch": 0,
        "vol": 8
      },
      "prompt_field": "audio_prompt",
      "voice_label_field": "voice_label",
      "voice_id_field": "voice_id"
    },
    "video": {
      "name_template": "{task_id}-omnihuman-video",
      "type": "video",
      "model": "OmniHuman 1.5",
      "modeType": "audio2video",
      "inputs": ["image", "audio"],
      "params": {
        "ratio": "auto",
        "resolution": "auto",
        "fastMode": 0,
        "count": 1
      }
    }
  },
  "acceptance": {
    "require_video_resolution": "720x1280",
    "check_actual_media_size": true,
    "on_resolution_mismatch": "fail_or_postprocess"
  },
  "execution_boundary": {
    "create_canvas": false,
    "create_nodes": false,
    "run_nodes": false,
    "requires_user_confirmation_for_paid_generation": true
  }
}
```

字段含义：

| 字段 | 规则 |
| --- | --- |
| `schema_version` | 接口配置 schema 版本，便于后续升级 |
| `interface` | 下游接口标识；当前为 `libtv_omnihuman` |
| `task_package.csv` | 与该接口配置配套的任务行 CSV |
| `defaults.target_*` | 成片验收目标；当前固定 `720x1280` |
| `defaults.voice_labels` | 业务默认音色；女声 `温暖闺蜜`，男声 `温润男声` |
| `defaults.voice_ids` | 已确认的 LibTV/TTS 音色 ID；`温暖闺蜜` 为 `Chinese (Mandarin)_Warm_Bestie`，`温润男声` 为 `Chinese (Mandarin)_Gentleman` |
| `defaults.voice_constraints` | 默认音频约束；语速 `speed=1.2`，音量 `volume=8`，写入音频节点时音量参数使用 LibTV schema 字段 `vol` |
| `nodes.*.name_template` | 执行器根据 `task_id` 生成 LibTV 节点名 |
| `nodes.*.model` | 当前接口使用的模型名 |
| `nodes.*.params` | 可直接写入对应 LibTV 模型 schema 的参数 |
| `nodes.*.prompt_field` | 从 CSV 哪一列读取 prompt |
| `acceptance` | 产物验收规则，不等价于模型参数 |
| `execution_boundary` | 明确此配置文件不授权建画布、建节点或付费生成 |

未来如果要输出 Oceanengine 任务包，应使用另一个接口配置，例如：

```json
{
  "schema_version": "interface-config/v1",
  "interface": "oceanengine",
  "task_package": {
    "csv": "<task>.csv",
    "plan": "<task>.plan.md"
  },
  "fields": {
    "person_prompt": "image_prompt",
    "script": "audio_prompt",
    "aspect_ratio": "aspect_ratio",
    "voice": "voice_label"
  },
  "execution_boundary": {
    "preflight": false,
    "import": false,
    "run_paid_video": false
  }
}
```

因此，**接口差异放配置文件，不放任务 CSV**。

## 推荐 LibTV 任务 CSV 字段

CSV 只保留逐条任务需要变化的数据。建议字段如下：

```csv
task_id,title,notes,
image_prompt,audio_prompt,voice_label,voice_id,aspect_ratio
```

字段说明：

| 字段 | 规则 |
| --- | --- |
| `task_id` | 保持源任务唯一 ID，只含字母、数字、短横线、下划线 |
| `title` | 人类可读标题 |
| `notes` | `{品类}+{序号}`，继承现有规则 |
| `image_prompt` | 从静态人物首帧属性派生，不含口型、眨眼、运镜等时序指令 |
| `audio_prompt` | 纯口播文案，不含 `[[NO_SPLIT]]` |
| `voice_label` | 用户语义音色；女声默认 `温暖闺蜜`，男声默认 `温润男声` |
| `voice_id` | LibTV/TTS schema 可识别的音色 ID；默认女声为 `Chinese (Mandarin)_Warm_Bestie`，未知时留空 |
| `aspect_ratio` | 任务意图比例，默认 `9:16`；具体模型参数仍由 interface JSON 决定 |

示例行：

```csv
task_id,title,notes,image_prompt,audio_prompt,voice_label,voice_id,aspect_ratio
jierou-01,洁柔抽纸 1,洁柔抽纸+1,"23岁亚洲女生，圆脸，清透肤色，黑色中长发低马尾，浅蓝衬衫配米白针织马甲，坐在自然光办公室工位前，桌面有洁柔抽纸、电脑和水杯，正面半身，人物居中，轻微微笑，手机固定竖屏9:16，真实生活记录感，自然光，真实肤质，无字幕，无Logo，无水印，无直播间，无广告棚。","下午在工位吃点小零食，桌面和手边总会需要纸巾。我这次放的是洁柔抽纸，抽放在电脑旁不占地方，擦手、擦桌面都顺手。看到淘宝闪购最高12元无门槛红包，我就顺手补了一提，办公室用起来少翻包找纸。",温暖闺蜜,Chinese (Mandarin)_Warm_Bestie,9:16
```

## 推荐 Markdown 计划格式

`<task>.libtv.plan.md` 建议包含：

1. 批次信息：来源品类、利益点、数量、生成日期。
2. 接口配置摘要：读取 `<task>.libtv.interface.json` 中的图片模型、音频模型、视频模型及参数。
3. 每条任务的数据行与三节点映射预览。
4. 风险提示：首帧图是否可能画错商品、音色是否明确、OmniHuman 模式是否需单条校验。
5. 执行边界：只生成任务包，不提交 `libtv node --run`。

每条任务建议展示为：

```text
task_id: jierou-01
title: 洁柔抽纸 1

image:
  node: jierou-01-image
  model: Z-image Turbo
  source: interface JSON `nodes.image`
  prompt: ...

audio:
  node: jierou-01-audio
  model: Minimax-speech-2.8-turbo
  source: interface JSON `nodes.audio`
  script: ...
  voice_label: 温暖闺蜜

video:
  node: jierou-01-omnihuman-video
  model: OmniHuman 1.5
  modeType: audio2video
  source: interface JSON `nodes.video`
  inputs:
    - jierou-01-image
    - jierou-01-audio
```

## Skill 修改建议

建议在 `prompt-engineering/SKILL.md` 的 Output Modes 增加：

```text
- LibTV OmniHuman package:
  Create three reviewable handoffs from accepted copy/avatar results:
  - one UTF-8 `<task>.libtv.csv` containing per-row task data only;
  - one UTF-8 `<task>.libtv.interface.json` containing the interface, model, node,
    parameter, naming, and acceptance configuration;
  - one UTF-8 `<task>.libtv.plan.md` human review plan.
  This output must not create a LibTV canvas, run `libtv node --run`, or submit paid generation.
```

建议在 workflow 中补充：

```text
When the user requests LibTV/OmniHuman output, derive:
- `image_prompt` from visible first-frame attributes only;
- `audio_prompt` from the accepted plain script;
- `voice_label` from the configured semantic voice defaults;
- LibTV image/audio/video node settings from `<task>.libtv.interface.json`.

Preserve the full avatar prompt in the audit record, but do not feed it directly to OmniHuman.
Require an explicit one-row sample run before any batch submission.
```

## 试跑中发现的风险

### 1. OmniHuman 的 modeType 警告

这次使用：

```text
modeType=audio2video
```

CLI 创建视频节点时返回过：

```text
该模式将忽略已连接的图片输入
```

但最终生成任务仍然包含 `imageList` 和 `audioList`，且生成成功。下一步需要人工检查成片是否真的使用了首帧人物图。如果人物不稳定，需要继续测试：

```text
modeType=singleImage2video
```

或确认 LibTV 网页端 OmniHuman 推荐模式。

### 2. 商品图和 Logo 风险

当前 `person_prompt` 里直接写了：

```text
桌面有洁柔抽纸
```

图片模型可能画错包装、品牌字样或 Logo。批量前建议：

- 第一阶段先保证链路能跑通，不要求先上传品牌图或商品参考图；
- 无真实商品图时，仍应保留用户确认的商品名或品牌意图，允许继续生成样片和任务包；
- prompt 不可改为“桌面有一包日用抽纸”这类泛化商品描述，也不可把品牌只放在口播里表达；
- 品牌图上传、真实商品图参考和外观一致性校验作为后续增强，不阻塞首版 LibTV OmniHuman 流程；
- 如果后续必须保证品牌、包装或商品外观一致性，再把真实商品图或已审核素材作为上游参考。

### 3. 音色映射不完整

CSV 中的：

```text
voice=温暖闺蜜
```

`温暖闺蜜` 仍是业务语义标签，但它已经有确认的 LibTV/TTS `voice_id`。实现时不得回退到
旧的 `明朗女声` 或“默认年轻女声”口径。

默认语义音色统一为：

```text
女声 -> 温暖闺蜜 -> Chinese (Mandarin)_Warm_Bestie
男声 -> 温润男声 -> Chinese (Mandarin)_Gentleman
```

任务包导出规则：

- `voice_label` 必填，默认按性别写入 `温暖闺蜜` 或 `温润男声`；
- `温暖闺蜜` 的 `voice_id` 必填为 `Chinese (Mandarin)_Warm_Bestie`；
- `温润男声` 的 `voice_id` 必填为 `Chinese (Mandarin)_Gentleman`；
- 当用户显式指定其他音色时，必须同时保留原始用户音色意图和映射结果，避免静默替换；
- 未确认 `voice_id` 时，不得在文档、CSV 或计划里声称已经锁定具体 TTS 音色。

### 4. 付费/积分执行边界

文案生成、任务包导出、画布建节点、节点生成是四个不同授权层级。建议 skill 只负责前两层：

```text
生成内容 -> 导出 LibTV 任务包
```

实际执行：

```text
创建画布 -> 创建节点 -> --run 生成
```

必须单独由用户确认。

## 后续建议

1. 先用 3 条样本测试 OmniHuman 的人物一致性和商品图可控性。
2. 确认 `audio2video` 是否真的吃首帧图；如果不稳定，换模式或调整连接方式。
3. 给 `prompt-engineering` 增加 `libtv_omnihuman_package` 输出模式。
4. 再写一个独立执行器读取 `<task>.libtv.csv`，分阶段执行：
   - `prepare-canvas`
   - `create-image-audio`
   - `run-image-audio`
   - `create-video`
   - `run-video`
   - `export-report`

执行器也必须支持 `--limit 1`，默认只跑样片，不默认全量跑。
