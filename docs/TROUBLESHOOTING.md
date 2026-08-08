# Troubleshooting

## The app opens but AI is unavailable

Manual editing does not require an AI provider. Configure a cloud key in Settings or select Offline Mock. Check the AI panel status for the active provider and model.

## Cloud connection test fails

Confirm the key, model ID, endpoint, network, quota, and declared capabilities. The details dialog includes safe HTTP/error information but never displays a key. No automatic retries are performed.

## JarvisArt is Offline

Select **JarvisArt Local → Real Native**. Set the installed JarvisArt root if auto-detection does not find it, ensure its launcher and model files are installed, then choose **Start JarvisArt**. Do not point AI Lightroom at a model file directly; it needs the existing JarvisArt localhost bridge.

## Rendering or export fails

Open **Help → Open Logs Folder**, then share only a redacted diagnostic report. Verify enough free disk space and write permissions for the selected export folder.
