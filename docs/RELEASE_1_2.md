# AI Lightroom 1.2.0 — Photo Sets & Reusable Looks / 照片组与调色配方

Edit a set of photographs without losing your place, save a look for later, and see exactly what changed. Version 1.2.0 also adds visible AI execution stages, an EXIF privacy switch, and measured CPU-rendering improvements.

连续处理一组照片、保存可复用的风格、清楚看到哪些参数被改动。1.2.0 同时加入真实 AI 执行阶段、EXIF 隐私开关，以及经过实测的 CPU 渲染优化。

## Open a photo set / 打开一组照片

Use `Ctrl+O` to select several JPG/PNG files, or drag multiple photos into the app. Move through them with the arrows beside the canvas title or `Alt+←` / `Alt+→`; click the photo counter to jump by filename. Returning to a visited photo in the current set resumes its own edit state and undo/redo history. The first visit to a photo with saved work still asks whether to restore it.

用 `Ctrl+O` 多选 JPG/PNG，或拖入多张照片。画布标题栏箭头、`Alt+←` / `Alt+→` 用于切换，点击照片计数可按文件名跳转。回到当前组里已编辑的照片时，继续它自己的编辑和撤回/重做历史；首次打开有持久编辑记录的照片，仍会询问是否恢复。

This is a navigation workflow, not batch editing/export. If the current session cannot be saved, navigation stops and keeps the current photo open. Export refuses all original paths in the current photo set.

这是组内导航，不是批量调色或批量导出。当前会话无法保存时，程序停止切换并保留正在编辑的照片。导出拒绝覆盖当前照片组内的任何原图。

## Save a grading recipe / 保存调色配方

From the toolbar, choose **配方 → 将当前调色存为配方… / Recipes → Save current grading as recipe…** and enter a name. On another photo, choose that name to apply the look as one undo step. Recipes remain in local application settings after the app closes; deleting a recipe does not alter photographs already edited with it.

在工具栏选择**配方 → 将当前调色存为配方…**并命名。切到另一张照片，点该名称应用风格，整个操作只需一次撤销。配方保存在本机应用设置里，关闭程序后仍可使用；删除配方不会改变已经用它调过的照片。

A recipe replaces basic tone/colour, HSL, curves, grading, detail, effects, and calibration. It leaves optics, geometry, masks, and watermarks specific to the destination photo untouched. The existing Copy/Paste Adjustments commands retain their broader scope, including optics and geometry.

配方替换基础明暗/色彩、HSL、曲线、分级、细节、效果和校准，保留目标照片专属的光学、几何、蒙版与水印。原有复制/粘贴调整命令继续保留较广范围，包括光学和几何。

## Review only what changed / 集中查看已改参数

In **调色 / Adjustments**, turn on **仅看已调整 / Changed only**. Blue labels and section counts mark non-default parameters; dots identify changed HSL colours, curve channels, and grading regions. Combine the filter with search, and use the reset button beside a value to undo just that parameter in one history step. Grading now exposes shared Blending and Balance controls.

在**调色**页勾选**仅看已调整**。蓝色标签和分组计数标记偏离默认值的参数，圆点标记有改动的 HSL 颜色、曲线通道和分级区域。可同时使用搜索；数值旁的复位按钮只恢复该参数，并形成一次历史步骤。色彩分级新增共用的融合和平衡控件。

The empty canvas has an explicit Open Photo button. The sampled RGB histogram labels dark, middle, and bright tones, and clears its clipping state when the photo is cleared. Horizontal wheel gestures no longer cause unintended image zoom.

空画布新增明确的打开照片按钮。预览采样 RGB 直方图标出暗部、中间调和高光，清空照片时同步清空裁切状态；横向滚轮手势不再误触图像缩放。

## Know what AI is doing / 看清 AI 正在做什么

The AI panel reports actual preparation, local/cloud waiting, validation, and rendering stages alongside elapsed time. It does not invent a percentage or remaining duration. High-resolution local inference can take minutes.

AI 面板显示真实的准备、等待本地/云端模型、校验和渲染阶段，以及已经用掉的时间；不编造百分比或剩余时长。高清本地推理可能需要数分钟。

**取消等待 / Cancel waiting** prevents the returned plan from being applied and remains visibly pending until the current operation safely returns. It cannot recall a cloud request already sent, and a local model may continue processing its submitted request. Duplicate sends remain blocked. Cloud retry is manual; automatic reinspection stays off by default and can add at most one extra call when explicitly enabled.

**取消等待**阻止返回方案应用，并持续显示取消中，直到当前操作安全返回。它无法撤回已经发出的云端请求，本地模型也可能继续处理已提交任务。重复发送仍被禁止。云端只手动重试；自动复检默认关闭，明确开启后最多增加一次请求。

## Choose whether exports include location data / 决定导出是否携带位置信息

Under **设置 → 性能与导出 → 导出 EXIF / Settings → Performance & Export → Export EXIF**, **保留拍摄信息（可能含 GPS 位置） / Keep photographic information (may include GPS)** remains enabled by default. Turn it off before sharing to omit photographic EXIF, including GPS, from new exports. The original photograph is unchanged. Full-resolution JPG/PNG rendering, masks, and watermarks remain independent of preview quality.

**设置 → 性能与导出 → 导出 EXIF**中的**保留拍摄信息（可能含 GPS 位置）**默认开启。分享前取消此项，新导出的照片会去除摄影 EXIF，包括 GPS；原始照片不变。全尺寸 JPG/PNG 渲染、蒙版和水印仍独立于预览质量。

## Measured renderer improvement / 渲染器实测改进

Paired CPU-rendering medians at a 1280 px longest edge improved from **58.63 to 30.74 ms** for contrast-only edits and from **198.46 to 157.54 ms** for basic edits. The benchmark alternates the baseline and candidate execution order, with five measured runs per case after warm-up. It measures rendering, not AI inference or end-to-end interface latency.

1280 px 长边的配对 CPU 渲染中位耗时：纯对比度编辑从 **58.63 降至 30.74 ms**，基础编辑从 **198.46 降至 157.54 ms**。基准交替运行新旧版本，预热后每种情况各测五次；测量对象是渲染器，不是 AI 推理或界面端到端延迟。

Contrast/basic/single-colour HSL outputs were pixel-identical at the measured sizes. Heavy edits differed by at most one 8-bit channel level, affecting at most **0.000106% of channels**. High-resolution heavy editing still takes seconds. See the benchmark for complete cases, hardware, and a reproduction script.

实测尺寸下，纯对比度、基础和单色 HSL 输出逐像素相同；重编辑最多相差一个 8 位通道等级，最多影响 **0.000106% 的通道**。高分辨率重编辑仍需要数秒。完整案例、硬件与复现脚本见性能报告。

The Windows build passed 241 automated tests and started successfully from the packaged executable. The AI stage and cancellation tests used controlled responses; the real JarvisArt inference in the 1.1 notes was not repeated for this release.

Windows 构建通过了 241 项自动测试，打包后的 EXE 已实际启动。AI 阶段显示和取消测试使用受控响应；1.1 版记录的真实 JarvisArt 推理，本次未重复运行。

## Download and learn / 下载与使用

Existing provider credentials, local models, watermarks, and sessions remain separate from the application package. A working JarvisArt bridge does not require a fresh model download for this update.

已有 Provider 凭据、本地模型、水印与会话独立于程序包保存。本地 JarvisArt bridge 已能工作时，本次更新不需要重新下载模型。

- [Windows installer and portable ZIP / Windows 安装包与绿色 ZIP](https://github.com/Garry-Tang-274/AI-Lightroom/releases/tag/v1.2.0)
- [User guide / 使用指南](https://github.com/Garry-Tang-274/AI-Lightroom/blob/v1.2.0/docs/USER_GUIDE.md) · [中文使用指南](https://github.com/Garry-Tang-274/AI-Lightroom/blob/v1.2.0/docs/USER_GUIDE_zh-CN.md)
- [Model download and setup / 模型下载与配置](https://github.com/Garry-Tang-274/AI-Lightroom/blob/v1.2.0/docs/GETTING_STARTED.md) · [中文新手指南](https://github.com/Garry-Tang-274/AI-Lightroom/blob/v1.2.0/docs/GETTING_STARTED_zh-CN.md)
- [Paired renderer benchmark / 渲染器配对实测](https://github.com/Garry-Tang-274/AI-Lightroom/blob/v1.2.0/docs/benchmarks/README.md)
