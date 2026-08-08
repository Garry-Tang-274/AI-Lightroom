# Contributing

Thank you for improving AI Lightroom.

1. Open an issue before large changes.
2. Keep the renderer non-destructive and preserve the single shared `EditorState`/`EditingPlan` contract.
3. Do not add API keys, user photos, model weights, cache files, or private paths.
4. Add focused tests for changed behavior and run `python -m pytest -q`.
5. Keep provider-specific logic inside provider adapters; the UI and renderer must remain provider-neutral.
6. Submit small, clear pull requests with a user-facing summary and test result.

By contributing, you agree that your contribution may be distributed under the MIT License.
