# Custom OpenAI-compatible API

Custom mode is for services that genuinely implement an OpenAI-compatible Chat Completions API. It is not a promise that every arbitrary URL is compatible.

Fill these fields in **File → Settings → AI**:

- Provider Name
- Base URL, including its compatible version path (often `/v1`)
- API Key
- Model ID
- Optional Organization / Project
- Optional custom headers as a JSON object with string keys and values
- Vision and structured-output capability declarations

Authentication headers cannot be overridden in Custom Headers; use the API Key field instead. A connection test is an explicit minimal request and may incur provider usage.

For a local server, leave Vision disabled unless its model and endpoint genuinely accept image URLs. With Vision disabled, use state-aware text edits rather than asking the provider to inspect an image.
