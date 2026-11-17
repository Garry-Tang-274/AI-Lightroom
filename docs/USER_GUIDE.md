# User guide

[简体中文](USER_GUIDE_zh-CN.md)

## Open a photo and find an adjustment

Open a JPG or PNG with **文件 → 打开图片 / File → Open**, `Ctrl+O`, or drag it into the canvas. Loading runs in the background; the original file is kept separate from the editable preview.

The right side has **调色 / Adjustments** and **AI 助手 / AI Assistant** tabs, with the histogram above them. In Adjustments, expand a group or search by Chinese/English name: `曝光`, `Exposure`, `HSL`, or `Grain`. Clearing the search restores the earlier expanded groups. History, masks, and watermarks are in the left sidebar.

- Drag a slider for live feedback; release it to create one undo step.
- During the drag, a fast preview follows **Settings → Performance & Export → Performance mode**: Balanced (default) caps the longest edge at 1280 px, Battery at 768 px, and Fine interaction at 1600 px. Release restores the selected Low/High working quality; export always uses the full original dimensions.
- Type an exact number in the value field. Double-click the slider to restore that parameter's default, including nonzero defaults such as geometry scale.
- The mouse wheel scrolls the panel without changing slider values, numeric fields, or selectors.
- In Curves, click to add a control point, drag to adjust it, and right-click an intermediate point to remove it. **重置 / Reset** resets the selected channel.

## Compare and concentrate

Hold **按住原图 / Original** on the toolbar for a quick before view, or press `\` to toggle it. For a simultaneous comparison, use **左右对比 / Split comparison** or `C`, then drag the dividing line: original on the left, current edit on the right. Press `C` again to leave this view.

Use **视图 → 专注模式 / View → Focus mode** or `Ctrl+Tab` to hide both sidebars; repeat to restore them. `F` fits the photo, and `1` shows working-preview pixels at 100%. This is not a full-resolution-original inspection mode.

## Local masks

In the left **蒙版 / Masks** tab, choose a type and click **添加 / Add**. Select the layer, then **显示蒙版 / Show mask** to inspect its red overlay before changing local exposure or colour.

- **Linear gradient:** edit start/end X and Y.
- **Radial gradient:** edit centre, radii, rotation, and feathering.
- **Luminance range:** set lower/upper brightness limits and feathering.
- **Colour range:** set target hue, tolerance, minimum saturation, and feathering.
- **Brush:** enable **在图片上绘制 / Paint on image**, set size, hardness, and opacity, then paint. Select **擦除笔触 / Erase strokes** to remove painted coverage.

Coordinates run from 0 to 1 across the photo, with the origin at the top left. Layers can be disabled, inverted, or deleted. Local semantic masks use conservative image analysis, not a large segmentation model; inspect the overlay and use a brush or mathematical mask when the region is unreliable.

## Watermarks

The left **水印 / Watermarks** tab imports PNG/JPG/WEBP into the local watermark library and adds a non-destructive layer. Choose a corner, the centre, or **自定义 / Custom**; Custom exposes horizontal and vertical position controls. Size, opacity, and margin display percentages. One drag is one undo step.

**移除图层 / Remove layer** removes it only from this photo. **从库删除 / Delete from library** deletes the stored asset after confirmation; do not use it merely to hide a watermark. Use **显示水印 / Show watermark** instead. A stored asset can be renamed or selected as the default for later photos.

## Reuse and recover edits

**编辑 → 复制调整 / Edit → Copy adjustments** (`Ctrl+Alt+C`) and **粘贴调整 / Paste adjustments** (`Ctrl+Alt+V`) reuse global tone, HSL, curves, grading, detail, effects, optics, geometry, and calibration. Photo-specific masks and watermarks are not copied.

`Ctrl+Z` undoes a change; `Ctrl+Y` or `Ctrl+Shift+Z` redoes it. Click a history entry to return to that state. Sessions save the current state, a bounded history window, and the selected history position in application settings rather than beside the original photo. Reopen the same unchanged source file and choose **恢复编辑 / Restore edits** to continue, including available redo steps, or decline to start from the original.

## AI editing

Configure a provider under **文件 → 设置 → AI 服务 / File → Settings → AI service** (`Ctrl+,`). In the right **AI 助手 / AI Assistant** tab, enter the intended result and send with `Ctrl+Enter`; `Enter` inserts a new line.

During a request, conflicting edits and duplicate submission are disabled. A validated plan is applied as one undoable transaction. Failures leave the current edit unchanged; a response that changes no parameters is reported as such. Unsupported JarvisArt operations remain listed in adjustment details.

Cloud requests have no automatic retry. Use **重新尝试 / Retry** only when you want another request. Automatic reinspection is off by default; enabling it can add one more call. **取消等待 / Cancel waiting** prevents the result from being applied but cannot recall a request already sent to a provider. The local daily safety cap is not the provider's live remaining quota.

**性能与导出 / Performance & Export** lets AI input quality follow the canvas or use Low/High independently. Dragging's temporary fast preview does not change that setting. Visual calls send a capped JPEG preview, not the original file. JarvisArt Local GGUF runs through a separate localhost service; Mock modes are blocked from real editing. See [JarvisArt setup and shared-service use](JARVISART.md).

## Export a separate finished photo

Use `Ctrl+S` or `Ctrl+Shift+S`, choose JPG/PNG, and save to another filename. The app refuses the current original path. JPEG quality is configurable; PNG is lossless. Export renders the original dimensions with the current parameters, masks, and watermarks, regardless of preview quality.

The exporter writes a temporary file before replacing the chosen output, so a failed encoding does not truncate an existing export. Available photographic metadata is retained; imported ICC colours are converted to the editor's sRGB working space. For errors, use **帮助 → 打开日志文件夹 / Help → Open logs**, or copy safe diagnostic details from the AI panel.
