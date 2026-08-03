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
| `reference_image_uri` | 可选；平台素材 URI，用于商品参考图约束人物图生成 |
| `reference_image_url` | 可选；参考图签名 URL，可留空由 Auto Oceanengine 运行时补取 |
| `reference_image_pid` | 可选；参考图 PID，无值时留空 |

使用标准 CSV 写入处理逗号、中文引号和换行。文件名采用规范化品类、批次和日期，且不得
覆盖已有文件。不提供参考图时三个 `reference_image_*` 字段写空字符串，下游仍按默认文生图
流程生成数字人图片；提供 `reference_image_uri` 时，下游会把参考图传入人物图片生成的
`images[]`。

字幕稿与 CSV 导出相互独立。生成态文案中的 `[[NO_SPLIT]]` 标签仅供字幕分句，
导出 `script` 前必须移除；添加标签本身不得触发 CSV 创建、覆盖、导入或视频生成。

## 提示词映射

当前下游链路先用 `person_prompt` 生成静态人物图，再用人物图、音色和 `script` 生成口播
视频。完整数字人视频 Prompt 不会被视频创建接口消费，必须单独留档。

从完整视频 Prompt 派生 `person_prompt` 时只保留首帧可见内容，目标长度 120–180 个中文字符：

- 开头先写 `竖屏9:16，固定中景，手机实拍，数字人口播首帧`，而不是生活方式抓拍；
- 人物外观、主流日常审美服装、发型、表情和静态姿态；
- 单一生活场景和背景道具；场景只作为背景，不驱动人物做准备、收拾、换鞋、低头看桌面、
  看包或看商品等动作；
- 商品位置、朝向、完整性和视觉关系；商品必须位于人物面前的桌面、餐桌、台面或办公桌上，远离人物双手；
- 仅商品本体或商品包装可以包含商品自带 logo，非商品区域无 logo；
- 禁止手持商品；禁止商品出现在人物身后、背后、背景里、远处、侧后方、沙发、玄关、购物袋或画面边缘；
- 人物不看商品、不接触商品；
- 正面、人物居中、眼睛直视镜头，身体稳定不做动作；
- 无字幕、文字贴片、水印、直播间和广告棚。

删除口型同步、眨眼、节奏、一镜到底、运镜、HDR、8K、电影级、暖色调等冗余或时序指令。

## 执行边界

只有用户另行要求即创预检时，才在目标项目中读取暂存 CSV 并运行：

```bash
uv run jichuang preflight \
  '/Users/sakana/Desktop/Work/Codex/Prompt Engineering/<YYYYMMDD>/<task>/<task>.csv'
```

暂存 CSV 不等于写入目标项目。预检通过也不等于授权导入或付费生成。只有用户分别明确
授权后，才能执行 `import` 或 `run-api-video`。提交结果不确定时不得重试，先核对平台
任务引用。
