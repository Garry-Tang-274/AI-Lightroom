# User guide

[简体中文](USER_GUIDE_zh-CN.md)

## Open a photo and find an adjustment

Click **打开照片 / Open photo** on the empty canvas, use **文件 → 打开图片 / File → Open** or `Ctrl+O`, or drag JPG/PNG files into the canvas. The file dialog supports multiple selection; dropping several photos also creates a photo set. Loading runs in the background; original files stay separate from editable previews.

Use the arrows beside the canvas title or `Alt+←` / `Alt+→` to move through the set. Click the `1 / 5` counter to jump directly to a named photo. Each photo retains its own edit state and undo/redo history: returning to a visited photo in the current set resumes those edits. The first visit to a photo with a saved session still asks whether to restore it. The group is navigation, not a batch-edit or batch-export command.

The right side has **调色 / Adjustments** and **AI 助手 / AI Assistant** tabs, with the histogram above them. In Adjustments, expand a group or search by Chinese/English name: `曝光`, `Exposure`, `HSL`, or `Grain`. Clearing the search restores the earlier expanded groups. History, masks, and watermarks are in the left sidebar.

Enable **仅看已调整 / Changed only** to review parameters that differ from their defaults. Blue labels and the group counts mark changed values; a dot beside an HSL colour, curve channel, or grading region identifies changes outside the selected channel. Search and this filter can be combined. The count covers global controls, not masks or watermarks.

- Drag a slider for live feedback; release it to create one undo step.
- During the drag, a fast preview follows **Settings → Performance & Export → Performance mode**: Balanced (default) caps the longest edge at 1280 px, Battery at 768 px, and Fine interaction at 1600 px. Release restores the selected Low/High working quality; export always uses the full original dimensions.
- Type an exact number in the value field. Click its reset icon or double-click the slider to restore that parameter's default, including nonzero defaults such as geometry scale. A reset is one undo step.
- The mouse wheel scrolls the panel without changing slider values, numeric fields, or selectors.
- In Curves, click to add a control point, drag to adjust it, and right-click an intermediate point to remove it. **重置 / Reset** resets the selected channel.
- Colour Grading includes shared **分级融合 / Blending** and **分级平衡 / Balance** controls below the selected shadows/midtones/highlights controls.

The histogram is sampled from the current preview. Its high-light percentage counts pixels with any RGB channel at 255; the black percentage counts pixels with all channels at 0. It is not a RAW-sensor clipping measurement.

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

### Save a look as a recipe

1. Grade one photo, then open the toolbar's **配方 / Recipes** menu (also under **编辑 → 调色配方 / Edit → Grading recipes**).
2. Choose **将当前调色存为配方… / Save current grading as recipe…**, enter a name, and save. Replacing an existing name asks for confirmation.
3. Move to another photo and choose the saved name from **配方 / Recipes**. This replaces the corresponding grading values and creates one undo step. An already-identical look creates no empty history entry.

Recipes include basic adjustments, HSL, curves, grading, detail, effects, and calibration. They preserve the destination's optics, geometry, masks, and watermarks. They contain parameters, not photo pixels, and remain in local application settings after restart. **删除配方 / Delete recipe** removes the saved recipe, not edits already applied to photos.

### Copy once, or resume previous work

**编辑 → 复制调整 / Edit → Copy adjustments** (`Ctrl+Alt+C`) and **粘贴调整 / Paste adjustments** (`Ctrl+Alt+V`) reuse global tone, HSL, curves, grading, detail, effects, optics, geometry, and calibration. Photo-specific masks and watermarks are not copied.

`Ctrl+Z` undoes a change; `Ctrl+Y` or `Ctrl+Shift+Z` redoes it. Click a history entry to return to that state. Sessions save the current state, a bounded history window, and the selected history position in application settings rather than beside the original photo. Reopen the same unchanged source file and choose **恢复编辑 / Restore edits** to continue, including available redo steps, or decline to start from the original.

## AI editing

Configure a provider under **文件 → 设置 → AI 服务 / File → Settings → AI service** (`Ctrl+,`). In the right **AI 助手 / AI Assistant** tab, enter the intended result and send with `Ctrl+Enter`; `Enter` inserts a new line.

During a request, the panel shows observed stages—configuration check, preview preparation, local/cloud waiting, validation, and rendering—and elapsed time. These are work-state updates, not an estimated completion percentage. High-resolution local inference can take minutes. Conflicting edits and duplicate submission are disabled. A validated plan is applied as one undoable transaction. Failures leave the current edit unchanged; a response that changes no parameters is reported as such. Unsupported JarvisArt operations remain listed in adjustment details.

Cloud requests have no automatic retry. Use **重新尝试 / Retry** only when you want another request. Automatic reinspection is off by default; enabling it can add one more call. **取消等待 / Cancel waiting** requests cancellation and prevents the result from being applied; the panel stays in a cancelling state until the current operation safely returns. It cannot recall a cloud request already sent, which may still count or cost money, and a local model may continue running its submitted request. The local daily safety cap is not the provider's live remaining quota.

**性能与导出 / Performance & Export** lets AI input quality follow the canvas or use Low/High independently. Dragging's temporary fast preview does not change that setting. Visual calls send a capped JPEG preview, not the original file. JarvisArt Local GGUF runs through a separate localhost service; Mock modes are blocked from real editing. See [JarvisArt setup and shared-service use](JARVISART.md).

## Export a separate finished photo

Use `Ctrl+S` or `Ctrl+Shift+S`, choose JPG/PNG, and save to another filename. The app refuses to overwrite any original in the current photo set, not just the photo on screen. JPEG quality is configurable; PNG is lossless. Export renders the original dimensions with the current parameters, masks, and watermarks, regardless of preview quality.

The exporter writes a temporary file before replacing the chosen output, so a failed encoding does not truncate an existing export. Under **设置 → 性能与导出 → 导出 EXIF / Settings → Performance & Export → Export EXIF**, **保留拍摄信息（可能含 GPS 位置） / Keep photographic information (may include GPS)** is on by default. Turn it off before sharing to omit photographic EXIF, including GPS, from new exports. It does not alter the original file. Imported ICC colours are converted to the editor's sRGB working space.

For errors, use **帮助 → 打开日志文件夹 / Help → Open logs**, or copy safe diagnostic details from the AI panel. For measured CPU-rendering improvements and their test conditions, see the [paired benchmark](benchmarks/README.md).
