# Two everyday editing workflows / 两种日常修图方式

## Start with manual editing / 先从手动编辑开始

Open a JPG or PNG, adjust exposure and white balance, then use curves and HSL for the remaining colour work. Use the original-view control and the histogram to check the result before exporting a separate file with `Ctrl+Shift+S`.

打开 JPG 或 PNG，先调整曝光和白平衡，再用曲线与 HSL 完成其余调色。导出前结合原图对比与直方图检查，使用 `Ctrl+Shift+S` 另存一份成片。

No model account is needed. Working-preview resolution affects interactive rendering; export is rendered from the original full-resolution image. This editor currently supports JPG/PNG, not a RAW development workflow.

不需要模型账号。工作预览尺寸影响交互渲染；导出从原始全分辨率图像重新渲染。目前支持 JPG/PNG，不是 RAW 显影流程。

## Use text as an editable starting point / 把文字方案当作可继续调整的起点

Choose a provider in Settings, then describe the desired treatment and the parts that must be preserved. For example: “Lower the saturation and cool the shadows; retain skin colour and highlight detail.” Inspect the applied controls and refine them manually rather than assuming the first plan is the final photograph.

在设置中选择服务商，说明希望怎样调整，以及哪些部分必须保留。例如：“降低饱和度，阴影偏冷；保留肤色和高光细节。”检查实际应用的参数，再手动修正，不把第一组方案直接当成最终成片。

A cloud provider receives the configured JPEG preview and edit state. JarvisArt Local requires a separately installed model and bridge. Mock providers are development fixtures and cannot analyse a real photograph.

云端服务商接收设定尺寸的 JPEG 预览和编辑状态。JarvisArt Local 需要另外安装模型与桥接服务。Mock 是开发样例，不能分析真实照片。

See [preview quality](../README.md#preview-quality--预览质量), [local setup](JARVISART_zh-CN.md), and [export controls](USER_GUIDE.md).
