# JarvisArt Manual AI Benchmark

This directory contains the repeatable **manual** benchmark protocol for a
future, verified local JarvisArt installation.  Do not add private photos,
API keys, model weights, presets produced from private photos, or cached model
responses to Git.

## Gate before running

Run this benchmark only when all conditions are true:

1. The model is obtained from the official `JarvisArt/JarvisArt-1208` page.
2. The official license remains available with the model and use is
   non-commercial/non-production.
3. The local device has enough GPU memory for the official BF16 checkpoint and
   its vision-generation runtime, without relying on an unverified community
   quantization.
4. A single test photo is explicitly authorized for local benchmarking.

## Fixed comparison

Use the same photo and prompt for:

- Gemini (current configured provider)
- Qwen (current configured provider)
- JarvisArt (official local checkpoint)

Record only non-sensitive measurements and exported public-safe result
artifacts outside this repository:

| Dimension | Required evidence |
| --- | --- |
| Input route | Preview dimensions and confirmation that the original was not uploaded for cloud tests |
| Parameter quality | Parsed plan/preset, supported operations, and explicitly unsupported operations |
| Renderer result | Same source image, visual before/after export, and local-mask coverage where applicable |
| Reliability | Request/model load duration, parse success/failure, and error category |
| Decision | Whether JarvisArt is better in native parameters, Lightroom-native rendering, or professional tool planning |

Integration is permitted only if JarvisArt wins at least one of those decision
criteria without silently dropping unsupported Lightroom operations.
