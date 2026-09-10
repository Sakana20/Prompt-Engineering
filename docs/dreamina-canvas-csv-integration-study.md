# Prompt Engineering 接入 Dreamina Canvas CLI 研究

日期：2026-09-10
研究对象：`prompt-engineering` Dreamina 输出适配器与 `dreamina-canvas` CLI 1.0.0

## 1. 当前结论

Dreamina 数字人口播采用两节点链路：

```text
image_prompt ──> 图片节点 ──> m2v 视频节点
                               └─ video_prompt 内嵌完整口播文案
```

不创建 TTS 或音频节点。图片节点通过真实 Node ID 同时建立 `--ref node:<id>` 上游连线，
并以 `{{node:<id>}}` 出现在视频 Prompt 正文中。该方案去除了音色目录、1.2x 语速参数和音频
时长依赖造成的执行阻断。

它仍不是已经验证的批量数字人能力：Prompt 内嵌文案能否稳定逐字说完、实际声音、口型和视频
时长都必须通过一条获批付费样片验证，不能因为节点请求被接受就宣称效果已经成立。

## 2. 已核验的平台能力

- CLI 版本：`1.0.0`，公开中国区版本。
- 当前用户指定模型名为 `seedance_2.0mini`；本次实时查询因登录失效而未能确认其 canonical
  名称和动态参数，执行前必须重新运行 `model find`。
- 视频 Prompt 最长 15000 字符，当前 80–100 字口播加完整数字人描述可放入 Prompt。
- 支持 `9:16`、`720p`，时长范围 4–30 秒，步长 1 秒。
- 视频节点可以只保存草稿；`--run`、报价和积分批准保持为独立步骤。

模型目录会变化。真实执行前必须重新查询 `schema` 与 `model list/find`，只使用实时返回的
canonical model 和参数；本文件不能代替运行时发现。

## 3. 语义来源与字段

Dreamina 适配器以经过全批校验的上游任务 JSON 为语义源，不直接把 Oceanengine CSV 当作
唯一来源。每条 Dreamina CSV 使用：

```csv
task_id,title,notes,image_prompt,video_prompt,aspect_ratio,reference_image_key
```

- `image_prompt`：静态数字人口播首帧 Prompt；有商品参考图时由执行层转换为 Dreamina 可用
  的图片资源或节点。
- `video_prompt`：从完整 `avatar_prompt` 派生，并直接包含去除 `NO_SPLIT` 标签后的完整口播。
- `reference_image_key`：包外稳定资产登记键，不保存签名 URL。
- Oceanengine URI/PID 不是 Dreamina Node ID，禁止混用。

视频 Prompt 使用以下合同：

```text
让{{node:<image-node-id>}}中的人物保持首帧身份与服装，<avatar_prompt>。
鼓励人物在口播过程中根据文案语义自然接触、拿起或使用商品，动作真实克制。
必须严格按照以下口播文案逐字说完，不得省略、改写、截断或提前结束：
“<完整纯口播文案>”。口型与口播内容同步，身体动作自然，不包含任何字幕。
```

Dreamina 视频适配层会移除静态首帧带入的“不手持商品”“不拿起商品”“不接触商品”、固定
机位、不切镜、一镜到底、不运镜和不推拉摇移等限制；静态首帧、Oceanengine 和 LibTV
规则不变。

## 4. 三件套接口

独立输出：

```text
<task>.dreamina.csv
<task>.dreamina.interface.json
<task>.dreamina.plan.md
```

接口配置版本为 `dreamina-interface-config/v2`。节点图只包含 `image` 和 `video`：

- 图片默认候选：`seedream_4.6`，无参考图 `t2i`，有参考图 `i2i`；
- 视频用户指定候选：`seedance_2.0mini + m2v + 9:16 + 720p`，执行前以实时发现结果为准；
- 视频输入只有 `image`；
- 视频时长由调用方结合口播长度显式提供，并满足实时模型 4–30 秒约束；
- 配置和计划均不创建线上画布、节点或付费任务。

## 5. 视频节点草稿

在人审完成并取得真实图片 Node ID 后：

```bash
avatar-prompts save-dreamina-video-node \
  --input <task>.dreamina.csv \
  --interface <task>.dreamina.interface.json \
  --task-id <task-id> \
  --project-id <project-id> \
  --image-node-id <image-node-id> \
  --duration <seconds> \
  --dry-run
```

该命令完成本地校验、替换 `{image_node_id}`、确认正文中形成有效节点引用，并把图片作为唯一
`--ref` 传给官方 CLI。去掉 `--dry-run` 后也只保存线上视频节点草稿，不附加 `--run`。

## 6. 校验与授权边界

任何线上写入前检查：

1. 任务 CSV/JSON 编码、必填字段和唯一 `task_id`；
2. `image_prompt` 通过当前视觉 Prompt 校验；
3. `video_prompt` 含且只含一个 `{image_node_id}` 占位符；
4. 完整纯口播原文确实出现在 `video_prompt`；
5. Prompt 包含逐字说完、不得省略改写截断或提前结束、`不包含任何字幕`；
6. 图片 Node ID 来自 Dreamina 当前画布或已持久化的公开状态；
7. 实时模型支持 `m2v` 图片单引用、比例、分辨率和时长；
8. 保存与运行使用稳定身份，恢复时不更换提交标识；
9. 最新报价未超过用户明确批准的积分上限。

任务包生成不创建画布；保存视频节点草稿不运行生成；图片生成和视频生成分别报价、分别取得
明确批准。批量前先做一条样片，检查人物一致性、商品外观、实际口播完整度、声音、口型、
时长和字幕情况。

## 7. 风险判断

直接把文案写入视频 Prompt 简化了节点图，也消除了当前 CLI 不支持 TTS 1.2x 的硬阻断，但
牺牲了独立音频节点对音色、语速和确定性台词的控制。当前接口只能要求模型逐字说，不能事先
证明它一定做到。因此该路径适合先做样片验证；在样片通过前，不应直接开放大批量付费生成。

## 8. 实现状态

- Oceanengine CSV 和 LibTV OmniHuman 三件套保持不变。
- Dreamina CSV 已删除 `audio_prompt`、`voice_intent`、`dreamina_voice_name`。
- Dreamina interface 已升级到 v2，并删除 `nodes.audio` 和全部语速门禁字段。
- `save-dreamina-video-node` 已删除 `--audio-node-id`，生成命令只传图片引用。
- 完整口播从 `marked_script` 去除控制标签后确定性嵌入视频 Prompt。
- 本地打包仍不创建画布、节点或付费生成。
