# Dreamina Canvas 任务包契约

当用户要求 Dreamina/即梦画布任务包时，使用 CLI 的
`package --format dreamina_canvas_package`。该格式只写本地交接文件，不创建画布、节点，
不报价，也不提交付费生成。

## 三件套

- `<task>.dreamina.csv`：每行保存 `task_id`、`title`、`notes`、`image_prompt`、
  `audio_prompt`、`video_prompt`、`aspect_ratio`、`voice_intent`、
  `dreamina_voice_name`、`reference_image_key`。
- `<task>.dreamina.interface.json`：保存画布、图片、TTS、视频节点配置和执行边界。
- `<task>.dreamina.plan.md`：保存人审内容、节点关系和已知阻断项。

## 固定决策

- `dreamina_voice_name` 必须为实时音色目录中的精确值`明媚女声`。
- 目标语速为 1.2x。Dreamina Canvas CLI 1.0.0 没有 TTS 语速参数；接口配置必须使用
  `speech_speed_enforcement=unsupported_by_dreamina_cli_1.0.0` 和
  `on_unsupported_speech_speed=stop_before_audio_run`。不得静默按 1.0x 执行或捏造
  `--speed`。
- `video_prompt` 必须从完整 `avatar_prompt` 派生，不得用静态 `image_prompt` 代替；任务包中
  保留唯一 `{image_node_id}` 占位符。
- 选择图片和音频引用后，用真实图片 Node ID 替换 `{image_node_id}`，再把最终 Prompt 写入
  视频节点；图片和音频必须分别作为 `--ref node:<id>` 传入。
- 最终 Prompt 必须要求完整使用音频节点的全部内容、逐字说完，不得省略、改写、截断或提前
  结束，并精确包含 `不包含任何字幕`。
- Dreamina 视频阶段允许人物触碰商品，并默认允许切镜或运镜。适配器必须移除上游带入的
  `不接触商品`、`不触碰商品`、`固定机位`、`不切镜`、`一镜到底`、`不运镜`、
  `不推拉摇移`等限制；只有用户另行要求时才添加。该放宽不得修改静态首帧、Oceanengine 或
  LibTV Prompt 的规则。
- 图片、音频连线使用 Dreamina 返回的 Node ID；不得把 Oceanengine URI/PID 当作
  Dreamina 引用，也不得把签名 URL 写入恢复状态。

显式保存视频节点草稿时使用：

```bash
avatar-prompts save-dreamina-video-node \
  --input <task>.dreamina.csv \
  --interface <task>.dreamina.interface.json \
  --task-id <task-id> \
  --project-id <project-id> \
  --image-node-id <image-node-id> \
  --audio-node-id <audio-node-id> \
  --duration <verified-seconds>
```

先追加 `--dry-run` 做本地参数验证。正式调用只保存节点草稿；该封装不会附加 `--run`。

模型和能力目录会变化。真实执行前重新查询 schema、canonical model 和完整分页音色目录。
图片、TTS 和视频运行分别报价并取得明确批准；图片和音频输入可被模型接受，不等于已经验证
稳定口型同步，批量前先做一条获批样片。

## 视频节点草稿

用户明确要求线上写入后运行：

```text
avatar-prompts save-dreamina-video-node \
  --input <task>.dreamina.csv \
  --interface <task>.dreamina.interface.json \
  --task-id <task-id> \
  --project-id <project-id> \
  --image-node-id <image-node-id> \
  --audio-node-id <audio-node-id> \
  --duration <verified-seconds>
```

该命令调用官方 `dreamina-canvas node create video`，把最终 Prompt 传给视频节点并同时建立
图片、音频上游连线。命令不带 `--run`，只保存草稿；`--dry-run` 会继续传给官方 CLI，仅做
本地校验且不写线上状态。
