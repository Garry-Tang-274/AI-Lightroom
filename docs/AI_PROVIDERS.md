# AI providers

Every provider returns the same strict `EditingPlan`. The provider registry owns provider creation and capability metadata; the renderer never depends on an AI vendor.

## Cloud providers

Gemini, OpenAI, and Qwen support a configured visual model and send only a capped JPEG preview. DeepSeek is intentionally registered as **text/state only**: it can be used for incremental changes such as “reduce saturation slightly”, but the application rejects a visual request when the provider has not declared vision support.

Cloud connection tests are explicit user actions and may consume quota. Normal requests do not auto-retry. The local daily budget counts a request as soon as it is sent, even when a response later fails validation.

## Configuration

Keys are read in this order: matching environment variable, then Windows Credential Manager. Settings never write keys into source-controlled files. Model IDs are editable text so provider model changes do not require an application update.

| Provider | Key environment variable | Optional endpoint variable |
| --- | --- | --- |
| Gemini | `GEMINI_API_KEY` | — |
| OpenAI | `OPENAI_API_KEY` | — |
| Qwen | `DASHSCOPE_API_KEY` | `QWEN_BASE_URL` |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL` |
| Custom | `AI_LIGHTROOM_CUSTOM_API_KEY` | `AI_LIGHTROOM_CUSTOM_BASE_URL` |

See [Custom API](CUSTOM_API.md) and [JarvisArt Local](JARVISART.md).
