# Changelog

## 1.2.0 - 2026-11-27 — Photo Sets & Reusable Looks / 照片组与调色配方

- Added multi-select opening and multi-photo drag-and-drop, title-bar navigation, `Alt+←` / `Alt+→`, and a photo-picker counter. Revisiting a photo in the current set resumes its own state/history; first recovery from saved work still asks for confirmation.<br>
  新增多选打开、多图拖入、画布标题栏导航、`Alt+←` / `Alt+→` 与计数跳转；回访当前组内照片续接各自编辑/历史，首次恢复持久记录仍询问。
- Added persistent named grading recipes with one-step undo when applied. Recipes retain tone/HSL/curves/grading/detail/effects/calibration and leave the target photo's optics, geometry, masks, and watermarks intact.<br>
  新增可跨启动保存的命名调色配方，应用可一次撤销；包含明暗/HSL/曲线/分级/细节/效果/校准，保留目标照片的光学、几何、蒙版和水印。
- Added changed-parameter highlighting, group counts, a changed-only filter, individual reset buttons, and grading blending/balance. Improved the empty-canvas open action and histogram labels; horizontal wheel input no longer accidentally zooms the photo.<br>
  新增已改参数高亮、分组计数、仅看已调整、单项复位及分级融合/平衡；改进空画布打开入口与直方图标签，横向滚轮不再误缩放照片。
- Added observed AI execution stages and elapsed time, with clearer cancellation state. Cancelled or late results remain unapplied; cloud retry stays manual. JarvisArt remains a separate local service, and Mock is not real image analysis.<br>
  新增真实 AI 执行阶段、耗时及清晰的取消状态；取消或晚到结果不应用，云端仍只手动重试。JarvisArt 保持独立本地服务，Mock 不冒充真实看图。
- Added an EXIF export setting, on by default; turning it off removes photographic EXIF including GPS from new exports. Export also protects other originals in the current photo set, and failed session saving blocks navigation rather than discarding edits.<br>
  新增默认开启的 EXIF 导出开关；关闭后新成片去除摄影 EXIF，包括 GPS。导出同时保护当前照片组内其他原图；会话保存失败时阻止切换，保留编辑。
- Reduced CPU-rendering temporary allocations and unused calculations. Paired results include 1280 px contrast rendering from **58.63 ms to 30.74 ms**, and basic edits from **198.46 ms to 157.54 ms**; conditions and numerical comparisons are in the benchmark.<br>
  减少 CPU 渲染临时数组与无用运算。配对测试中，1280 px 对比度编辑由 **58.63 ms 降至 30.74 ms**，基础编辑由 **198.46 ms 降至 157.54 ms**；测试条件与数值差异见性能报告。

[Bilingual release notes / 双语发布说明](docs/RELEASE_1_2.md) · [Renderer benchmark / 渲染性能实测](docs/benchmarks/README.md) · [中文更新日志](CHANGELOG_zh-CN.md)

## 1.1.1 - 2026-11-17 — Windows packaging / Windows 打包修复

- Prevented the build environment's unrelated ICU libraries from shadowing the Windows ICU used by Qt. Added executable-level startup checks to stop broken packages before release.
- 避免构建环境中其他软件的 ICU 库遮蔽 Qt 所需的 Windows 系统库；加入 EXE 启动检查，阻止不可启动的程序包发布。
- Background smoke capture no longer displays a window or takes desktop focus.
- 后台启动截图不再显示窗口或抢占桌面焦点。

## 1.1.0 - 2026-11-17 — Workspace & Reliability

- Reorganised the dark workspace into Adjustments and AI Assistant tabs, with searchable/collapsible parameter groups, a persistent histogram, background image loading, a draggable before/after split (`C`), and focus mode (`Ctrl+Tab`).
- Added performance-mode-driven interactive previews while dragging: Balanced (default) caps the longest edge at 1280 px, Battery at 768 px, and Fine interaction at 1600 px. Release returns to the selected Low/High quality; AI input and full-resolution export remain independent.
- Fixed wheel changes in numeric fields/selectors, nonzero slider resets, stale HSL/grading channel values, and duplicate-x curve edits. Added editable gradient/range-mask geometry and exact custom watermark positions.
- Preserved the selected history position and redo branch on recovery. Watermark and curve interactions are complete undo transactions; AI work disables conflicting edits and avoids empty success history entries.
- Hardened JarvisArt data parsing and AI error handling while preserving one default cloud request, no automatic retry, visible unsupported operations, and cancellation checks. Closing the app no longer stops a shared JarvisArt service.
- Fixed the local-adjustment vignette crash, cumulative watermark opacity, preview/export watermark sizing, mask-cache precision drift, and ICC working-space handling. Reduced unnecessary rendering work and image-sized temporaries.
- Export now refuses the source photo and replaces its output atomically only after encoding succeeds. Added regression coverage for the repaired editing, rendering, AI, and recovery paths.

[中文更新日志](CHANGELOG_zh-CN.md) · [Bilingual release guide / 双语发布指南](docs/RELEASE_1_1.md)

## 1.0.3 - 2026-08-09

- Expanded the deterministic Develop pipeline with JarvisArt-compatible detail, luminance/color noise reduction, post-crop vignette controls, grain, defringe, geometry, primary calibration, color grading, split-toning aliases, and RGB/R/G/B tone-curve support.
- Reworked the local JarvisArt Lua boundary to parse complete top-level Develop tables without executing Lua. Structural preset metadata is no longer misreported as a missing pixel operation; genuinely unavailable Lightroom-only operations remain explicit.
- Added matching non-destructive editor controls, preview/export rendering, history/undo state, and copy/paste support for the new controls.
- Replaced the desktop shortcut artwork with a high-contrast aperture icon designed to remain legible at Windows icon sizes.

## 1.0.2 - 2026-08-09

- Added low/high/automatic working-preview selection. High quality rebuilds a larger local preview and, when a visual request is needed, sends the same configured JPEG maximum edge to the AI provider. User-supplied JarvisArt Local GGUF defaults to high; cloud providers default to low.
- Added an independent AI image-quality control so the visible preview and the vision-request preview can be chosen separately.
- Blocked JarvisArt Local's fixture-backed Mock mode from silently applying a fixed demonstration plan. It now states that it cannot inspect photos and directs users to Local GGUF or a configured cloud provider.
- Promoted the user's existing local llama.cpp / Qwen2-VL GGUF bridge to the primary local provider profile, with a clear Local GGUF label and no cloud request fallback.
- Replaced the first-release dark icon with a brighter, high-contrast aperture icon in the executable, installer, ZIP, and desktop shortcut.
- Added bilingual onboarding and installer documentation for the preview-quality controls and the real-versus-Mock JarvisArt boundary.

## 1.0.1 - 2026-08-09

- Replaced the application and desktop-shortcut artwork with a new high-resolution minimalist aperture icon; packaging now preserves the curated source icon.
- Added the per-user Windows installer build, installer documentation, and a Chinese first-run guide covering manual editing, cloud AI, Custom API, JarvisArt model downloads, and troubleshooting.
- Clarified the boundary between JarvisArt's official API/inference workflow and AI Lightroom's explicit localhost bridge interface.

## 1.0.0 - 2026-08-09

- Public-release preparation: documentation, security guidance, notices, CI, and Windows packaging.
- Added official local JarvisArt localhost integration, lifecycle controls, and strict native-plan adaptation.
- Added DeepSeek text/state provider metadata and expanded Custom OpenAI-compatible settings.
- Added drag-and-drop image opening, recent files, slider reset/exact input, diagnostics, logs shortcut, and updated shortcuts.
- Retained deterministic, non-destructive rendering, local masks, watermarks, history, export, and cloud cost protection.

## Earlier development history

The complete Git history is retained. Earlier commits were not assigned public semantic-version tags because there is insufficient evidence that they were separately released artifacts.
