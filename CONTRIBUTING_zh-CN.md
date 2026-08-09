# 贡献指南

> English: [CONTRIBUTING.md](CONTRIBUTING.md)

感谢你帮助改进 AI Lightroom。

1. 大型改动请先创建 Issue 讨论。
2. 保持渲染器为非破坏性，并维护唯一共享的 `EditorState`/`EditingPlan` 契约。
3. 不要提交 API Key、用户照片、模型权重、缓存文件或私人路径。
4. 为改动行为添加聚焦测试，并运行 `python -m pytest -q`。
5. Provider 专属逻辑应位于 Provider adapter 内；UI 与渲染器必须保持 Provider 中立。
6. 提交小而清晰的 Pull Request，并附用户可读的摘要和测试结果。

提交贡献即表示你同意该贡献可依据 MIT License 分发。
