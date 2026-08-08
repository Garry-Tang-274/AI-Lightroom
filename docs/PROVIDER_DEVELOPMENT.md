# Provider development

AI Lightroom providers are small adapters. They must never mutate pixels, UI controls, history, or `EditorState` directly.

## Contract

1. Create a module under `app/ai/` or `app/ai/<provider>/` that subclasses `AIProvider`.
2. Implement `plan(PlanningRequest) -> EditingPlan`; validate all provider output with the strict Pydantic schema.
3. Raise `AIRequestError` for safe user-facing failures. Do not log prompts, previews, authorization headers, or keys.
4. Add a `ProviderDescriptor` and factory in `app/ai/provider_registry.py`. Declare vision and structured-output capability honestly, along with `cost_type` and `privacy_type`.
5. Add fixture tests. Tests must not call paid APIs or require a model download.

The orchestrator owns preview construction, optional reinspection limits, atomic execution, and mask reliability checks. The executor maps `EditingPlan` to the common `EditorState`, ensuring manual adjustment, undo/redo, preview, and export stay provider-neutral.
