# JarvisArt Local

JarvisArt Local is an optional localhost provider. AI Lightroom does not bundle, download, move, or license JarvisArt code or model weights.

## Requirements

Install JarvisArt separately under any directory that contains its existing `scripts/launch_services.ps1` launcher and local backend. In AI Lightroom choose **JarvisArt Local → Real Native**, optionally set the root directory and endpoint (default `http://127.0.0.1:8765`), then select **Start JarvisArt** or make the first JarvisArt request.

The provider checks `/health`, starts only the selected existing launcher, and connects through localhost. It sends a temporary reduced JPEG preview to the bridge and removes that temporary file immediately after the request. It does not upload the original photo or count against cloud AI usage.

## Lifecycle

The settings panel reports Offline, Loading, Ready, or Error. **Stop and release GPU** stops only processes launched by the current AI Lightroom process; shared services started by Lightroom Classic or another tool are not killed. Closing AI Lightroom has the same ownership rule.

## Current bridge scope

The current JarvisArt local bridge returns Lightroom global parameters and some HSL parameters. AI Lightroom maps supported settings to `EditingPlan` and lists unsupported Lightroom operations instead of silently pretending to apply them. Native local masks and Lightroom-only operations remain a future bridge capability.

JarvisArt may be governed by a separate non-commercial license. Read and follow JarvisArt's own repository and model license before use.
