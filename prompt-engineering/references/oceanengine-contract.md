# Auto Oceanengine 任务契约

## 目标项目

默认目标目录：

```text
/Users/sakana/Desktop/Work/Codex/Auto Oceanengine 26.6.22
```

写入前读取目标项目的 `AGENTS.md` 和当前 `README.md`。目标目录权限不足时请求用户授权，
不得绕过沙箱。

## CSV 暂存

任务文件使用 UTF-8 CSV，默认写入：

```text
/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task>.csv
```

字段固定为：

| 字段 | 规则 |
|---|---|
| `task_id` | 唯一；只含字母、数字、短横线和下划线 |
| `person_prompt` | 必填；静态人物图提示词 |
| `script` | 必填；已校验的纯口播，不含 `[[NO_SPLIT]]` 控制标签 |
| `aspect_ratio` | 默认 `9:16` |
| `voice` | 当前使用 `明朗女声` |
| `title` | 简短任务标题 |
| `notes` | 使用 `{用户输入品类}+{序号}`，例如西瓜批次写 `西瓜+1`，雨伞批次写 `雨伞+1` |

使用标准 CSV 写入处理逗号、中文引号和换行。文件名采用规范化品类、批次和日期，且不得
覆盖已有文件。

字幕稿与 CSV 导出相互独立。生成态文案中的 `[[NO_SPLIT]]` 标签仅供字幕分句，
导出 `script` 前必须移除；添加标签本身不得触发 CSV 创建、覆盖、导入或视频生成。

## 提示词映射

当前下游链路先用 `person_prompt` 生成静态人物图，再用人物图、音色和 `script` 生成口播
视频。完整数字人视频 Prompt 不会被视频创建接口消费，必须单独留档。

从完整视频 Prompt 派生 `person_prompt` 时只保留首帧可见内容：

- 人物外观、服装、发型、表情和静态姿态；
- 单一生活场景和背景道具；
- 商品位置、朝向、完整性和视觉关系；
- 禁止手持商品，商品只作为桌面、台面、购物袋、沙发、玄关或手边的静态可见物出现；
- 9:16、固定中景（不允许使用半身景别）、正面、人物居中、眼睛直视镜头；
- 自然光、手机实拍、真实肤质；
- 无字幕、Logo、水印、直播间和广告棚。

删除口型同步、眨眼、节奏、一镜到底、运镜等时序指令。

## 执行边界

只有用户另行要求即创预检时，才在目标项目中读取暂存 CSV 并运行：

```bash
uv run jichuang preflight \
  '/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task>.csv'
```

暂存 CSV 不等于写入目标项目。预检通过也不等于授权导入或付费生成。只有用户分别明确
授权后，才能执行 `import` 或 `run-api-video`。提交结果不确定时不得重试，先核对平台
任务引用。
