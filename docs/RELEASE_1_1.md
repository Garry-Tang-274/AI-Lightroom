# AI Lightroom 1.1 — Workspace & Reliability / 工作区与稳定性升级

## Start with the new workspace / 从新工作区开始

Open a photo, then use the right **调色 / Adjustments** tab. Expand only the controls you need or search in Chinese/English. The adjacent **AI 助手 / AI Assistant** tab gives the prompt and result their own space. The left sidebar still holds history, masks, and watermarks.

打开照片后使用右侧**调色**页：只展开需要的分组，或直接用中英文搜索参数。旁边的 **AI 助手**页给指令与结果留出独立空间。左侧仍是历史、蒙版与水印。

- `C`: compare original (left) and edited (right), then drag the divider.<br>
  `C`：左原图、右调整，拖动分隔线对比。
- `Ctrl+Tab`: hide/show sidebars. `Ctrl+,`: open Settings.<br>
  `Ctrl+Tab`：隐藏/恢复侧栏；`Ctrl+,`：打开设置。
- Drag for a fast preview; release to restore the selected working quality and record one undo step.<br>
  拖动看快速预览；松手恢复所选质量，并记录一次撤销。

Interactive preview follows **Settings → Performance & Export → Performance mode**: Balanced (default) caps the longest edge at 1280 px, Battery at 768 px, and Fine interaction at 1600 px. AI input quality and full-resolution export remain independent of this temporary interaction size.

交互预览跟随**设置 → 性能与导出 → 性能模式**：默认平衡最长边为 1280 px，省电为 768 px，精细交互为 1600 px。AI 发送质量和全分辨率导出不受这个临时交互尺寸影响。

## More precise controls / 更完整的手动控制

Gradient and range masks now expose their actual geometry and range values. Watermarks have exact percentage fields and custom X/Y positions. Numeric fields and selectors ignore the wheel; double-click restores the correct parameter default. HSL/grading channel changes retain current edits, and curve points no longer fail when added at an existing X coordinate.

渐变与范围蒙版可以直接修改区域和范围；水印有精确百分比及自定义 X/Y 位置。数值框与下拉框不响应滚轮，双击恢复正确默认值。HSL/色彩分级切换后保留当前调整，曲线加点与已有点同横坐标时不再报错。

## Reliable edits and output / 更可靠的编辑与导出

Recovery keeps the selected history position and available redo steps. AI runs as one guarded transaction; an unchanged response is reported without a fake successful edit. Cloud retry stays manual. Closing AI Lightroom leaves a shared JarvisArt service available to Lightroom Classic; explicit stop remains in Settings and only acts on services owned by the current app instance.

编辑恢复保留当前历史位置与可重做步骤。AI 作为一个受保护的事务执行；没有参数变化时会明确提示，不制造“成功编辑”。云端重试仍需手动发起。退出 AI Lightroom 保留共享 JarvisArt 服务，Lightroom Classic 可继续使用；设置中的停止按钮只作用于当前应用实例拥有的服务。

Export renders from the original dimensions and refuses to overwrite the source photo. It finishes encoding before atomically replacing the chosen output. Fixes also cover the local-adjustment crash, watermarks becoming fainter on repeated renders, preview/export watermark sizing, and ICC colour handling.

导出使用原始尺寸并拒绝覆盖原图；完成编码后才原子替换所选输出。另修复了局部调整崩溃、水印反复渲染变淡、预览/导出水印大小偏差与 ICC 色彩处理。

## Real local JarvisArt check / 真实本地 JarvisArt 验证

A single visual request to the development machine's existing GGUF `qwen2_vl` service used a **3072 × 1728** JPEG preview (**945,127 bytes**), with no cloud requests or new model downloads. It returned 29 native global fields and produced **16 changed editor-state fields**. Local inference took **238.172 s**; the full inference-to-render path took **241.09 s** for this run. The output's mean absolute pixel change was **5.9134 on the 0–255 scale**, and the input edit state remained unchanged.

在开发机已有 GGUF `qwen2_vl` 服务上完成一次真实视觉请求：输入为 **3072 × 1728** JPEG 预览（**945,127 字节**），没有云端请求或重新下载模型。返回 29 个原生全局字段，实际产生 **16 项编辑状态变化**。本次本地推理耗时 **238.172 秒**，推理到渲染全链耗时 **241.09 秒**；输出的像素平均绝对变化为 **5.9134 / 255**，输入编辑状态保持不变。

The returned `PointColors` operation was explicitly reported as unsupported and left unapplied.

返回的 `PointColors` 操作被明确标为不支持，未执行。

## Update and continue / 更新后继续使用

The release passed **194 automated tests**, including rendering, AI failure handling and request accounting, history transactions, isolated settings, and control interactions. The local JarvisArt run above is a separate real-model check; automated cloud tests use mocked responses and incur no API charges.

本版通过 **194 项自动测试**，涵盖渲染、AI 失败处理与请求计数、历史事务、设置隔离及控件交互。上方 JarvisArt 验证为独立的真实模型测试；自动化云端测试使用模拟响应，不产生 API 费用。

Download the [Windows installer or portable ZIP](https://github.com/Garry-Tang-274/AI-Lightroom/releases/latest). Existing provider settings, credentials, watermark assets, and recoverable sessions remain separate from the application package. JarvisArt models/runtimes are still separately installed; no model download is needed for this update if your local bridge already works.

下载 [Windows 安装包或绿色 ZIP](https://github.com/Garry-Tang-274/AI-Lightroom/releases/latest)。已有 Provider 设置、凭据、水印素材与编辑恢复数据独立于程序包保存。JarvisArt 模型与运行时仍单独安装；已有本地 bridge 能工作时，本次更新不需要重新下载模型。

The editor remains a JPG/PNG workflow with its own deterministic renderer, not an Adobe RAW engine. Inspect semantic masks before applying them; unsupported native Lightroom operations stay visible in AI details.

软件仍是使用自身确定性渲染器的 JPG/PNG 编辑流程，不是 Adobe RAW 引擎。应用语义蒙版前请检查选区；不支持的 Lightroom 原生操作会继续在 AI 详情中明确列出。

[User guide / 使用指南](USER_GUIDE.md) · [中文使用指南](USER_GUIDE_zh-CN.md) · [Model download and local setup / 模型下载与本地部署](GETTING_STARTED_zh-CN.md)
