# Provider 开发说明

[English](PROVIDER_DEVELOPMENT.md)

AI Lightroom 的 Provider 是小型适配器；它们绝不能直接修改像素、UI 控件、历史记录或 `EditorState`。

## 约定

1. 在 `app/ai/` 或 `app/ai/<provider>/` 下建立继承 `AIProvider` 的模块。
2. 实现 `plan(PlanningRequest) -> EditingPlan`，并用严格 Pydantic schema 验证所有输出。
3. 用户可见失败使用 `AIRequestError`；不要记录 prompt、预览、认证头或 Key。
4. 在 `app/ai/provider_registry.py` 注册 `ProviderDescriptor` 与 factory，诚实声明 Vision、structured output、成本与隐私能力。
5. 添加 fixture 测试；测试不得调用付费 API 或要求下载模型。

Orchestrator 负责预览构造、可选复检上限、原子执行和蒙版可靠性检查；Executor 将 `EditingPlan` 映射到通用 `EditorState`，保证手动调整、撤回/重做、预览和导出不绑定具体 Provider。
