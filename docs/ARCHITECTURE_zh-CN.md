# 架构

[English](ARCHITECTURE.md)

```text
原始像素 + EditorState + 蒙版/水印
                    │
               本地渲染器
              ├─ 预览 Worker
              └─ 全分辨率导出 Worker

指令 + 低清/高清预览 + EditorState
                    │
              Provider Registry
                    │
         严格 EditingPlan / Adapter
                    │
          executor → 单个历史事务
```

`EditorState` 是唯一编辑状态。预览渲染绝不会修改源像素；UI 只读取/修改该状态，并把耗时的渲染、导出、AI 请求与 JarvisArt Local GGUF 启动/推理交给 Worker。

JarvisArt Local GGUF 还有一层本地边界：localhost 返回 Lightroom 风格输出后，先变为 `JarvisArtNativePlan`，再由 `JarvisArtAdapter` 转成通用 `EditingPlan`。
