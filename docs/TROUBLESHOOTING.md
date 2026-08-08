# Troubleshooting

## The app opens but AI is unavailable

Manual editing does not require an AI provider. Configure a cloud key in Settings or select JarvisArt Local GGUF. Check the AI panel status for the active provider and model. Offline Mock is deliberately blocked from real editing because it cannot inspect a photograph.

## Cloud connection test fails

Confirm the key, model ID, endpoint, network, quota, and declared capabilities. The details dialog includes safe HTTP/error information but never displays a key. No automatic retries are performed.

## JarvisArt is Offline

Select **JarvisArt Local GGUF → Local GGUF**. Set the installed local-runtime root if auto-detection does not find it, ensure its launcher, GGUF, and projection files are installed, then choose **Start JarvisArt**. Do not point AI Lightroom at a model file directly; it needs the existing localhost bridge.

The official JarvisArt API and AI Lightroom's local bridge do not use the same port or request format. Read [JarvisArt Local](JARVISART.md) or the [中文部署与连接说明](JARVISART_zh-CN.md) before changing an endpoint.

## Rendering or export fails

Open **Help → Open Logs Folder**, then share only a redacted diagnostic report. Verify enough free disk space and write permissions for the selected export folder.
