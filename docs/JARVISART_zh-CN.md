# JarvisArt Local GGUF：部署、模型和连接说明

本页只描述真实可验证的边界：JarvisArt 是独立项目；AI Lightroom 是一个非破坏性照片编辑器。两者不会互相打包、不会共享 API Key，也不会把官方模型权重提交到本仓库。

## 1. 先确认许可证和硬件

请先阅读 [JarvisArt 官方仓库](https://github.com/LYL1015/JarvisArt) 与 [官方模型页](https://huggingface.co/JarvisArt/JarvisArt-1208)。官方仓库说明 JarvisArt 的权重、推理代码和相关资料按照其非商业许可证提供；商业使用需要向官方申请许可。

模型不是一个小插件。下载前请确认：

- 有足够的磁盘空间给权重、缓存和临时结果；
- 有可用的 NVIDIA CUDA GPU，或准备接受很慢的 CPU / offload 推理；
- 能接受官方环境可能更适合 Linux/WSL/服务器而不是普通 Windows 桌面机；
- 已经确认服务端口没有被其他程序占用。

AI Lightroom 不会下载或分发你的量化权重。你可以连接自己已经验证可用、并有使用权限的 GGUF / llama.cpp 本地运行时；不要把它误标为项目随附的官方权重。

## 2. 官方、可复现的最小验证：生成 `.lrtemplate`

官方 [Batch Inference Guide](https://github.com/LYL1015/JarvisArt/blob/main/docs/README_Inference.md) 把 Basic 模式定义为“仅生成 Lightroom 预设”。这条路线最适合先验证模型输出是否正确。

1. 克隆官方仓库，创建 Python 3.11 Conda 环境，安装 `envs/requirements_demo.txt`。
2. 按官方指南下载它指定的 `JarvisArt-preview` 权重到 `checkpoints/pretrained/JarvisArt-preview`，并确保配置中的 `model_name_or_path` 指向这个目录。
3. 启动 `llamafactory-cli api src/inference/config/qwen2_vl.yaml`，官方示例端口为 `8002`。
4. 在输入目录的每个子目录放入 `before.jpg` 或 `before.png` 和 `user_want.txt`。
5. 执行 `python inference.py --image_path <输入目录>`。
6. 看到 `output_image.lrtemplate` 后，用 Lightroom Classic 的 **Develop → Presets 面板加号 → Import Presets** 导入。

请以官方原文为准；上游更新命令、模型 ID、环境依赖或许可时，本项目不会静默替你改写上游流程。

## 3. AI Lightroom 的本地连接接口

AI Lightroom 的 **JarvisArt Local GGUF** 不是通用的“模型文件选择器”，而是一个 localhost 客户端。选择 **Local GGUF** 后，它会：

1. 检查 `http://127.0.0.1:8765/health`；
2. 只有健康检查返回 `status=ok` 和 `model_status=online` 才显示 Ready；
3. 将缩小的 JPEG 预览临时写入本机；
4. `POST /develop_settings`，提交 `photo_path` 和用户 `prompt`；
5. 读取返回的 Lightroom Lua 参数，映射仅限当前渲染器支持的参数；
6. 删除临时预览文件。

原图不会离开电脑；本地请求不消耗云端 API 预算。未知或当前不支持的 Lightroom 参数会在应用中显示为“未支持”，不会被伪装成已应用。

## 4. 如何在应用中设置

1. 打开 **文件 → 设置 → AI**。
2. Provider 选 **JarvisArt Local GGUF**。
3. 运行模式选 **Local GGUF（主力本地推理）**，不要选 Mock；Mock 仅供开发界面和事务流程验证，软件会阻止它执行真实调色，因为它不会分析照片。
4. **JarvisArt 根目录**填写包含 `scripts/launch_services.ps1` 的本地桥接服务目录；若没有这个启动器，应用不会猜测或篡改你的官方安装。
5. Endpoint 保持 `http://127.0.0.1:8765`，除非你的桥接服务明确使用其他本机端口。
6. 点击 **启动 JarvisArt**，等待状态变为 **Ready**。
7. 打开照片后在 AI 输入框中输入要求，按 `Ctrl+Enter`。一次成功方案作为一个完整的撤回事务处理。Local GGUF 的“自动”预览质量默认为高清（最长边默认 3072 px）；可在 **文件 → 设置 → 性能与导出** 改成低清或指定 AI 发送质量。

## 5. 状态解释

| 状态 | 意义 | 下一步 |
| --- | --- | --- |
| Offline Mock Test | 固定离线测试数据，绝不会读取或分析照片 | 切换到 Local GGUF 或云端 Provider。 |
| Offline | 没找到根目录或本地服务未启动 | 检查启动器路径、端口和服务日志。 |
| Loading | 服务已启动但模型尚未就绪 | 等待模型加载；不要重复点击发送。 |
| Ready | 健康检查通过 | 可发送一张照片的调色请求。 |
| Error / timeout | 服务启动或推理失败 | 查看服务日志、显存、端口占用和模型路径。 |

## 6. 常见误区

- **把官方 `8002` 端口直接填入 AI Lightroom**：不可行。官方 API 与本应用的 `8765 /develop_settings` 本地桥接接口不同。
- **只下载 `JarvisArt-1208` 就点“启动”**：不可行。权重还需要符合官方或桥接服务要求的推理运行时。
- **看到 Mock 返回方案就以为模型已跑通**：不对。Mock 从不加载模型，也不会分析照片；当前版本会直接阻止它对真实照片执行固定演示方案。
- **要求应用导入任何第三方量化文件**：当前发布版不把第三方量化权重作为官方部署路径。

## 7. 提交问题时需要的安全信息

可提供：Provider 状态、模型名、端口、脱敏后的 `/health` JSON、最近 100 行启动日志、GPU 显存错误、应用的错误详情。不要提供：API Key、完整照片、Windows 凭据导出、完整的用户目录。
