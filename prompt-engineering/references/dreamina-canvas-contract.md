# Dreamina Canvas 任务包契约

当用户要求 Dreamina/即梦画布任务包时，使用 CLI 的
`package --format dreamina_canvas_package`。该格式只写本地交接文件，不创建画布、节点，
不报价，也不提交付费生成。

## 三件套

- `<task>.dreamina.csv`：每行保存 `task_id`、`title`、`notes`、`image_prompt`、
  `video_prompt`、`aspect_ratio`、`reference_image_key`。
- `<task>.dreamina.interface.json`：保存画布、图片、视频节点配置和执行边界。
- `<task>.dreamina.plan.md`：保存人审内容、图片到视频的节点关系和已知限制。

## 固定决策

- Dreamina 链路只包含图片节点和视频节点，不创建 TTS 或音频节点。
- `video_prompt` 只使用选中的图片引用、商品互动方向和已通过校验的纯口播文案，不再写入
  `avatar_prompt` 中的人物、服装、场景或其他描述，也不得复制静态 `image_prompt`。去除
  `[[NO_SPLIT]]` 标签后，把完整口播文案直接写入 `video_prompt`；任务包中保留唯一
  `{image_node_id}` 占位符。
- 选择图片引用后，用真实图片 Node ID 替换 `{image_node_id}`，再把最终 Prompt 写入视频
  节点；只把图片作为 `--ref node:<id>` 传入。
- 最终 Prompt 必须包含`必须严格按照以下口播文案逐字说完`，并要求不得省略、改写、截断
  或提前结束；还必须精确包含`不包含任何字幕`。
- Dreamina 视频阶段鼓励人物根据口播语义自然接触、拿起或使用商品，动作真实克制，并默认
  允许切镜或运镜。适配器必须移除上游带入的`商品不由人物手持`、`不拿起商品`、
  `不接触商品`、`不触碰商品`、`固定机位`、`不切镜`、`一镜到底`、`不运镜`、
  `不推拉摇移`等限制；只有用户另行要求时才添加。该放宽不得修改静态首帧、Oceanengine 或
  LibTV Prompt 的规则。
- 当前配置使用用户指定的 `seedance_2.0mini`。执行前仍必须通过实时 `model find` 将其确认
  为 canonical model；若登录或目录发现失败，停止在视频节点写入前。
- 图片连线使用 Dreamina 返回的 Node ID；不得把 Oceanengine URI/PID 当作 Dreamina
  引用，也不得把签名 URL 写入恢复状态。
- `duration` 必须由执行者结合口播长度选择，并满足实时视频模型限制。Prompt 内嵌文案不保证
  模型一定逐字生成或使用指定声音，批量前必须先做一条获批样片检查。

显式保存视频节点草稿时使用：

```bash
avatar-prompts save-dreamina-video-node \
  --input <task>.dreamina.csv \
  --interface <task>.dreamina.interface.json \
  --task-id <task-id> \
  --project-id <project-id> \
  --image-node-id <image-node-id> \
  --duration <seconds>
```

先追加 `--dry-run` 做本地参数验证。正式调用只保存节点草稿；该封装不会附加 `--run`。

模型和能力目录会变化。真实执行前重新查询 schema 和 canonical model。图片和视频运行分别
报价并取得明确批准；图片输入与 Prompt 文案可被模型接受，不等于已经验证稳定口播、指定
音色或逐字一致性，批量前先做一条获批样片。

## 视频节点草稿

用户明确要求线上写入后运行：

```text
avatar-prompts save-dreamina-video-node \
  --input <task>.dreamina.csv \
  --interface <task>.dreamina.interface.json \
  --task-id <task-id> \
  --project-id <project-id> \
  --image-node-id <image-node-id> \
  --duration <seconds>
```

该命令调用官方 `dreamina-canvas node create video`，把最终 Prompt 传给视频节点并建立
图片上游连线。命令不带 `--run`，只保存草稿；`--dry-run` 会继续传给官方 CLI，仅做
本地校验且不写线上状态。
