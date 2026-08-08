# AI Lightroom V0.2

AI Lightroom is a Windows desktop photo editor with non-destructive local rendering and optional AI-assisted color-grading plans. AI analyzes a reduced preview and returns a validated `EditingPlan`; the local renderer applies only the supported deterministic adjustments, curves, HSL, and masks. It does not use generative image redrawing.

## Current features

- JPG/PNG import, fit/zoom, histogram, before/after, undo/redo, copy/paste adjustments.
- Basic tone/color controls, HSL, RGB/channel curves, color grading, local masks, brush masks, and non-destructive watermarks.
- Full-resolution JPG/PNG export with available EXIF, ICC, and DPI metadata.
- Non-destructive preview/export pipeline: original pixels + `EditorState` + masks/layers → render.
- Local AI usage guard with no automatic retry and an offline Mock provider.

## AI providers

The application does not provide an API key and never proxies photos or keys through a project-owned server. You select a service and use your own account; cloud services can charge for requests.

Formally supported now:

- Google Gemini
- OpenAI (high-quality AI mode)
- Alibaba Cloud Model Studio / DashScope: `qwen3.7-plus`
- Custom OpenAI-compatible API
- Offline Mock (no network)
- JarvisArt Local: a local native-output adapter. `Mock Native` is included for
  safe UI/renderer verification; `Real Native` remains a visible official-model
  runtime placeholder and never falls back to a cloud provider.

The provider registry declares each adapter's capabilities (vision, structured output, multi-image input, image generation/editing, streaming, and custom Base URL). Future adapters can be registered without changing the color-grading core.

### Configure a provider

Open **File → Settings → AI** and choose a provider.

- **Qwen**: enter your Model Studio API Key. Default model: `qwen3.7-plus`. Default Beijing Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`. Replace it with the region/workspace URL shown by your Model Studio console when needed.
- **Custom / OpenAI-compatible**: enter a provider name, Base URL ending in the compatible API version path (usually `/v1`), API Key, and Model ID. Enable Vision and structured JSON only when the service actually supports them.
- **JarvisArt Local**: no API key, no cloud budget, and no photo upload. Choose
  `Mock Native` to exercise the bundled native-plan adapter. `Real Native`
  currently reports that an official local runtime must be installed; it does
  not download weights or substitute a different model.
- **Test connection** sends one small, user-initiated text request. It may consume provider quota/cost.

API keys are stored in Windows Credential Manager, separately from normal settings. Environment variables override the credential store. Keys are never committed, logged, embedded in the EXE, or placed in the README.

Example local `.env` values (replace placeholders; do not commit this file):

```dotenv
GEMINI_API_KEY=YOUR_API_KEY_HERE
GEMINI_MODEL=gemini-3.6-flash
OPENAI_API_KEY=YOUR_API_KEY_HERE
OPENAI_MODEL=gpt-5.6-terra
DASHSCOPE_API_KEY=YOUR_API_KEY_HERE
QWEN_MODEL=qwen3.7-plus
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Cloud analysis sends a JPEG preview, capped by the configurable long edge (default 1536 px). Original high-resolution photos stay local and are used only for final export.

## Run

```powershell
Set-Location D:\AI-Lightroom
.\.venv\Scripts\python.exe -m app.main
```

AI input accepts multiple lines. Use `Ctrl+Enter` to send; `Enter` creates a new line.

## Develop and test

```powershell
Set-Location D:\AI-Lightroom
.\.venv\Scripts\python.exe -m pytest -q
```

## Build for Windows

```powershell
Set-Location D:\AI-Lightroom
.\scripts\build_windows.ps1
& '.\dist\AI Lightroom\AI Lightroom.exe' --smoke-test
```

## Known limits

- Input is currently JPG/PNG; RAW and a complete color-managed workflow are not implemented.
- Local semantic masks are conservative OpenCV-based analysis, not a large segmentation model.
- The project does not yet implement dedicated Claude, DeepSeek, Doubao, OpenRouter, SiliconFlow, or Ollama adapters. Services that genuinely expose OpenAI-compatible Chat Completions can use Custom mode.
- Image generation and generative image editing are intentionally not part of the AI color-grading pipeline.
