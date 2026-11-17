# AI Lightroom: Complete Getting-started Guide

[简体中文](GETTING_STARTED_zh-CN.md)

This guide starts at download. Manual editing needs neither an account nor a model. Cloud AI and JarvisArt Local are optional.

## 1. Install

### Recommended: Windows installer

1. Download `AI-Lightroom-<version>-Setup.exe` from the GitHub **Releases** page.
2. Run it and retain the default per-user destination unless you have a reason to change it.
3. Launch from Start, the optional desktop shortcut, or the installation folder.

The public build is not commercially code-signed yet, so Windows SmartScreen may identify an unknown publisher. Only download from the project Release, confirm the repository and version, and use the ZIP package if you prefer to inspect its contents first.

### Portable ZIP

1. Download `AI-Lightroom-<version>-windows-x64.zip`.
2. Extract the **entire** archive to a writable folder.
3. Run `AI Lightroom.exe`; do not start it from inside the compressed archive.

## 2. Edit and export without AI

1. Open a JPG/PNG using `Ctrl+O`, or drag it into the application.
2. Open the right **调色 / Adjustments** tab. Expand a group or search for `Exposure`, `HSL`, or a Chinese parameter name. Masks, brush masks, and watermarks are in the left tabs.
3. Sliders update a fast preview as you drag. Releasing restores the selected quality and creates one undo step, so one `Ctrl+Z` reverses the whole drag. Numeric fields allow exact input; the wheel scrolls without changing values.
4. Hold **按住原图 / Original**, or press `\`, for the unedited view. Press `C` for a draggable left-original/right-edited split; `Ctrl+Tab` hides the sidebars for a focused view.
5. Export with `Ctrl+S` or `Ctrl+Shift+S`. Choose a different filename: the app refuses the original path. Export renders from the original local pixels and current non-destructive edit state.

The current release supports JPG/PNG, not a RAW-development workflow.

## 3. Low / High preview and AI image quality

The toolbar menu labelled **Low preview** or **High preview** changes the visible working preview. The same controls are under **File → Settings → Performance & Export**.

| Choice | What happens |
| --- | --- |
| Automatic (default) | Cloud providers use Low to reduce transfer/cost. JarvisArt Local **GGUF** uses High because it is local and has no per-request cloud fee. |
| Low | Default maximum edge: 1536 px. Faster, economical for cloud vision. |
| High | Default maximum edge: 3072 px. More local memory/CPU, more visual detail. |

The **AI input image quality** control is independent: choose **Follow canvas**, **Always low**, or **Always high**. When a request requires visual analysis, the provider receives a JPEG at that chosen maximum edge. It never receives the original full-resolution photo.

Dragging temporarily uses a fast preview, then restores the chosen quality on release. Its maximum edge follows **Settings → Performance & Export → Performance mode**: Balanced (default) is 1280 px, Battery is 768 px, and Fine interaction is 1600 px. This does not reduce the AI request's configured image quality or the full-resolution export. The canvas 100% view is relative to working-preview pixels.

Small follow-ups such as “make it a little weaker” can be state-aware text requests and may deliberately omit an image. Say “look again at the current result” when a fresh visual inspection is needed.

## 4. Configure a cloud AI provider

Open **文件 → 设置 → AI 服务 / File → Settings → AI service**, choose a provider, enter your own API key and model ID, then use **Test connection**. `Ctrl+,` also opens Settings.

- **Gemini**, **OpenAI**, and **Qwen / DashScope** can perform visual analysis and return the same strict `EditingPlan`.
- **DeepSeek** is text/current-state only in this release; use it for incremental changes rather than first-pass image inspection.
- **Custom / OpenAI-compatible API** is for a service that actually supports OpenAI Chat Completions. Enter its display name, Base URL (normally including `/v1`), API key, model ID, and only the capabilities the service truly supports.

API keys are stored in Windows Credential Manager, never in the repository, release package, logs, or project settings. A cloud request has no automatic retry and normally maps to one user send action. The local daily safety limit defaults to 20; it is a safety cap, not a statement of the provider's live quota.

## 5. Send an AI editing request

1. Open a photo.
2. Open the right **AI 助手 / AI Assistant** tab and describe the intended photographic result, for example:

   ```text
   The image feels flat. Give it a subtle cinematic grade: darken the sky a little,
   keep the ground bright, natural, and avoid HDR.
   ```

3. Press `Ctrl+Enter` to send. `Enter` creates a new line.
4. Duplicate sending and conflicting edits are disabled while the request runs. A valid AI plan is committed as one undoable transaction; an unchanged plan is reported without adding an empty history entry.
5. Created local masks appear in the **Masks** panel and remain editable, hideable, and removable.

If a request fails, open **View adjustment details** for safe diagnostic information. It includes provider/model/status and validation fields, never your API key.

Retry is manual. Cancelling stops the result from being applied, but a cloud request already sent can still count toward provider usage. Automatic reinspection remains off unless you enable it in Settings.

## 6. JarvisArt Local: important boundary

JarvisArt is a separate project with its own code, model weights, runtime, and license. AI Lightroom does not bundle, download, or redistribute it.

- **Local GGUF** connects to an already-running compatible llama.cpp / Qwen2-VL localhost bridge. Automatic preview quality defaults to High.
- **Mock Native** is a fixed development fixture. It cannot see or understand the photo. AI Lightroom blocks it from applying a demonstration plan so it cannot be mistaken for real image analysis.

For official model download, `.lrtemplate` generation, Lightroom Classic import, and the local bridge boundary, read [JarvisArt Local](JARVISART.md) and [JarvisArt deployment (Chinese)](JARVISART_zh-CN.md).

Closing AI Lightroom leaves the shared local service running so a Lightroom Classic plugin can continue using it. Use **Settings → AI service → Stop and release GPU** only when you intend to stop a service owned by this app instance.

## 7. Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open image |
| `Ctrl+S` / `Ctrl+Shift+S` | Export / Export as |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` or `Ctrl+Shift+Z` | Redo |
| `\` | Original comparison |
| `C` | Draggable before/after split |
| `Ctrl+Tab` | Focus mode |
| `F` / `1` | Fit / 100% |
| `Ctrl+,` | Settings |
| `Ctrl+Alt+C` / `Ctrl+Alt+V` | Copy / paste adjustments |
| `Ctrl+Enter` | Send AI request |
| `Enter` | New line in AI prompt |

For common startup, provider, export, and path errors, see [Troubleshooting](TROUBLESHOOTING.md).
