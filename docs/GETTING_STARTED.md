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
2. Use the right panel for Basic controls, HSL, curves, masks, brush masks, and watermarks.
3. Sliders update the preview as you drag. Releasing a slider creates one undo step, so one `Ctrl+Z` reverses the whole drag.
4. Hold **Original** on the toolbar or press `\` to compare the unedited photo.
5. Export with `Ctrl+S` or `Ctrl+Shift+S`. Export renders from the original local pixels and non-destructive edit state; it does not overwrite the original unless you intentionally choose and confirm the same path.

The current release supports JPG/PNG, not a RAW-development workflow.

## 3. Low / High preview and AI image quality

The toolbar menu labelled **Low preview** or **High preview** changes the visible working preview. The same controls are under **File → Settings → Performance & Export**.

| Choice | What happens |
| --- | --- |
| Automatic (default) | Cloud providers use Low to reduce transfer/cost. JarvisArt Local **GGUF** uses High because it is local and has no per-request cloud fee. |
| Low | Default maximum edge: 1536 px. Faster, economical for cloud vision. |
| High | Default maximum edge: 3072 px. More local memory/CPU, more visual detail. |

The **AI input image quality** control is independent: choose **Follow canvas**, **Always low**, or **Always high**. When a request requires visual analysis, the provider receives a JPEG at that chosen maximum edge. It never receives the original full-resolution photo.

Small follow-ups such as “make it a little weaker” can be state-aware text requests and may deliberately omit an image. Say “look again at the current result” when a fresh visual inspection is needed.

## 4. Configure a cloud AI provider

Open **File → Settings → AI Providers**, choose a provider, enter your own API key and model ID, then use **Test connection**.

- **Gemini**, **OpenAI**, and **Qwen / DashScope** can perform visual analysis and return the same strict `EditingPlan`.
- **DeepSeek** is text/current-state only in this release; use it for incremental changes rather than first-pass image inspection.
- **Custom / OpenAI-compatible API** is for a service that actually supports OpenAI Chat Completions. Enter its display name, Base URL (normally including `/v1`), API key, model ID, and only the capabilities the service truly supports.

API keys are stored in Windows Credential Manager, never in the repository, release package, logs, or project settings. A cloud request has no automatic retry and normally maps to one user send action. The local daily safety limit defaults to 20; it is a safety cap, not a statement of the provider's live quota.

## 5. Send an AI editing request

1. Open a photo.
2. Describe the intended photographic result, for example:

   ```text
   The image feels flat. Give it a subtle cinematic grade: darken the sky a little,
   keep the ground bright, natural, and avoid HDR.
   ```

3. Press `Ctrl+Enter` to send. `Enter` creates a new line.
4. The button is disabled while a request is running. A valid AI plan is committed as one undoable transaction.
5. Created local masks appear in the **Masks** panel and remain editable, hideable, and removable.

If a request fails, open **View adjustment details** for safe diagnostic information. It includes provider/model/status and validation fields, never your API key.

## 6. JarvisArt Local: important boundary

JarvisArt is a separate project with its own code, model weights, runtime, and license. AI Lightroom does not bundle, download, or redistribute it.

- **Local GGUF** connects to an already-running compatible llama.cpp / Qwen2-VL localhost bridge. Automatic preview quality defaults to High.
- **Mock Native** is a fixed development fixture. It cannot see or understand the photo. AI Lightroom blocks it from applying a demonstration plan so it cannot be mistaken for real image analysis.

For official model download, `.lrtemplate` generation, Lightroom Classic import, and the local bridge boundary, read [JarvisArt Local](JARVISART.md) and [JarvisArt deployment (Chinese)](JARVISART_zh-CN.md).

## 7. Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open image |
| `Ctrl+S` / `Ctrl+Shift+S` | Export / Export as |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` or `Ctrl+Shift+Z` | Redo |
| `\` | Original comparison |
| `F` / `1` | Fit / 100% |
| `Ctrl+Enter` | Send AI request |
| `Enter` | New line in AI prompt |

For common startup, provider, export, and path errors, see [Troubleshooting](TROUBLESHOOTING.md).
