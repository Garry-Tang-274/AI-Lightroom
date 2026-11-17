# Changelog

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
