# 第三方声明

> English: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

AI Lightroom 源代码采用 MIT 许可证。其 Windows 发行版捆绑或依赖的第三方组件受各自条款约束。

| 组件 | 许可证 / 条款 | 在 AI Lightroom 中的用途 |
| --- | --- | --- |
| PySide6 / Qt | LGPL-3.0 或 GPL 替代条款 | 动态 Qt Python 绑定；重新分发时保留适用的 Qt/PySide 声明。 |
| OpenCV | Apache-2.0 | 图像操作与蒙版分析。 |
| Pillow | HPND 风格许可证 | 图像 I/O 与元数据。 |
| NumPy | BSD 风格 | 数组处理。 |
| SciPy / OpenBLAS | BSD 风格；适用二进制声明 | 可选数值计算辅助。 |
| Pydantic | MIT | Schema 验证。 |
| python-dotenv | BSD-3-Clause | 可选的本地环境配置。 |
| google-genai | Apache-2.0 | 可选 Gemini 客户端。 |
| OpenAI Python | Apache-2.0 | 可选 OpenAI-compatible 客户端。 |
| psutil | BSD-3-Clause | 本地诊断/服务归属。 |
| PyInstaller | GPL-2.0-or-later，附带其分发例外 | Windows 打包工具。 |

发布环境已于 2026-08-09 审查软件包元数据。本表只是声明摘要，不构成法律建议。发布构建者应保留已安装依赖随附的声明，尤其是 Qt/PySide 和二进制数值库的声明。

## JarvisArt

JarvisArt 代码、模型权重和许可证**不**包含在本仓库或发行版中。JarvisArt 是独立安装的可选组件，仍受其自身许可证（包括可能的非商业条款）约束。AI Lightroom 只提供 localhost Provider adapter。
