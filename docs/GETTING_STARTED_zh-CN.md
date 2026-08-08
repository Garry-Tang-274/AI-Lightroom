# AI Lightroom 中文新手完整指南

本指南从“刚下载软件”开始。你不需要 API Key、不需要 AI 模型，也能先完成完整的手动修图和导出；AI 与 JarvisArt 都是可选功能。

## 0. 先选一条最适合你的路

| 目标 | 建议路线 | 需要下载模型吗？ |
| --- | --- | --- |
| 只想修图、导出照片 | 直接使用 AI Lightroom | 不需要 |
| 想用自然语言调色，且愿意使用云端服务 | Gemini / OpenAI / Qwen 等云端 Provider | 不需要 |
| 想在本机研究 JarvisArt 并生成 Lightroom 预设 | 官方 JarvisArt 独立部署 | 需要 |
| 想把已准备好的本地 JarvisArt 服务连到本软件 | JarvisArt Local | 需要先准备本地桥接服务 |

> 重要：AI Lightroom 不会替你下载、上传或重绘原始照片。云端 AI 仅在你主动发送请求时接收设置中指定大小的 JPEG 预览；导出始终从你的本地原图重新渲染。

## 1. 安装和首次启动

### 方式 A：安装包（推荐）

1. 在 GitHub 的 **Releases** 页面下载 `AI-Lightroom-<版本>-Setup.exe`。
2. 双击安装包，保持默认安装位置即可；安装完成后，开始菜单和桌面均可启动。
3. 如果 Windows SmartScreen 提示“未知发布者”，原因是当前公开版尚未购买商业代码签名证书。请只从本仓库的 Release 下载，并核对版本号；不确定时先下载 ZIP 版查看内容。

### 方式 B：ZIP 绿色版

1. 下载 `AI-Lightroom-<版本>-windows-x64.zip`。
2. 右键压缩包，选择 **全部解压缩**。不要直接在压缩包预览窗口中启动程序。
3. 打开解压后的文件夹，双击 `AI Lightroom.exe`。

若程序无法启动，先阅读 [故障排除](TROUBLESHOOTING.md)；不要把整个文件夹放在只读目录或临时目录。

## 2. 第一次修图：不需要 AI

1. 打开程序后，按 `Ctrl+O`，或直接把 JPG / PNG 拖入窗口。
2. 在右侧调整 **曝光、对比度、高光、阴影、白色色阶、黑色色阶、色温、色调、饱和度、自然饱和度** 等参数。
3. 拖动滑块时画面会实时更新；松开鼠标才会生成一条历史记录，因此一次连续拖动可用一次 `Ctrl+Z` 撤回。
4. 使用 **HSL**、**曲线**、**蒙版** 或 **水印** 时，修改都仍是非破坏性的。
5. 按住工具栏的 **原图对比** 或按 `\`，可以查看未编辑原图。
6. 按 `Ctrl+S` 或 `Ctrl+Shift+S` 导出 JPG / PNG。原文件不会被覆盖，除非你在导出对话框中主动选了同一文件和确认覆盖。

支持格式是 JPG / PNG。当前公开版本不是 RAW 显影器，RAW 请先在相机软件或 Lightroom 中转换后再导入。

## 3. 使用云端 AI 调色

### 3.1 选择 Provider

在菜单选择 **文件 → 设置 → AI**。选择一个 Provider，输入你自己的 API Key，再点击 **测试连接**。可用项包括：

- **Gemini**：视觉理解与结构化调色方案。
- **OpenAI**：视觉理解与结构化调色方案。
- **阿里云百炼 / Qwen**：视觉理解与结构化调色方案。
- **DeepSeek**：当前定位为“文字 + 当前编辑状态”的增量微调，不用于首次视觉看图。
- **Custom / OpenAI-compatible**：适用于确实兼容 OpenAI Chat Completions 接口的第三方或本地服务。
- **Offline Mock**：只用于验证软件流程，不是真实 AI 分析。

选择后，界面底部的 AI 状态会明确显示当前是哪个 Provider 和模型。测试连接成功不代表每个模型都支持图片或严格 JSON；请使用服务商实际支持的模型 ID。

### 3.2 低清 / 高清预览，以及发送给 AI 的图片质量

工具栏中新增 **低清预览 / 高清预览** 菜单；也可以打开 **文件 → 设置 → 性能与导出** 配置：

1. **预览质量**可选“自动、低清、高清”。低清默认最长边是 **1536 px**，高清默认最长边是 **3072 px**，两个值都可改。
2. **自动**是默认值：云端 Provider 默认低清，避免无意增加上传量和费用；JarvisArt Local 的 **Real Native** 默认高清，因为它在本机处理，不产生云端调用费用。
3. **发送给 AI 的图像质量**可以选“跟随画布预览、始终低清、始终高清”。如果本次需要视觉分析，发送的 JPEG 会采用此处的最长边；原始全分辨率照片不会上传。
4. “弱一点、退一点、少一点”这类增量文字请求可能不会重新发送图片，这是状态感知的费用保护。若希望模型重新判断画面，请明确说“重新看看现在效果”。

### 3.3 API Key 安全和费用保护

- Key 由 Windows Credential Manager 保存，不写入项目文件、日志、Release 压缩包或 Git。
- 可以在设置页面修改或删除 Key；也可以用 `.env.example` 所列的环境变量临时覆盖。
- 默认 **一次点击发送最多产生一次云端请求**。失败不自动重试，照片也不会被改动。
- **AI 费用保护** 默认每日本地上限为 20 次。这只是软件的安全阀，不等于服务商后台的实时剩余额度。
- 达到上限后可等第二天自动恢复，或在设置中按自己的风险偏好修改上限；不建议禁用保护。

### 3.4 发送第一条指令

1. 先打开一张照片。
2. 在 AI 输入框写清楚目标，例如：

   ```text
   画面有点平。做轻微电影感：天空稍压暗，地面不要变暗，
   保持自然、不过度 HDR。
   ```

3. 按 `Ctrl+Enter` 发送；普通 `Enter` 只会换行。
4. 请求期间发送按钮会禁用，避免重复消耗额度。完成后，AI 方案会作为一整个可撤回事务写入历史记录。
5. 如果 AI 建议天空或其他区域的局部调整，结果会出现在 **Masks** 面板；你可以继续手动修改、隐藏或删除。

若看到 API 错误，点 **查看错误详情**。它会展示安全的 HTTP 状态、Provider 信息和校验字段，但不会显示 API Key。

## 4. Custom / OpenAI-compatible API

仅当目标服务明确提供 OpenAI Chat Completions 兼容接口时才使用 Custom：

1. 在 **文件 → 设置 → AI** 中选择 **Custom / OpenAI-compatible API**。
2. 填写 Provider 名称、Base URL（通常包含 `/v1`）、API Key 和 Model ID。
3. 按目标服务的真实能力勾选 Vision 和 Structured Output；不确定时不要把它们当作支持。
4. 点击 **测试连接**，成功后再回到照片页面发送请求。

不能通过“随便填一个 URL”把任意服务伪装成兼容服务。自定义 Header 不能覆盖 `Authorization`，避免意外把 Key 写进配置或日志。详细字段说明见 [Custom API](CUSTOM_API.md)。

## 5. JarvisArt：下载官方模型、生成 Lightroom 预设与连接本软件

JarvisArt 是独立项目，受其自己的许可证约束。AI Lightroom **不包含、不自动下载、也不重新分发** JarvisArt 的代码或权重。官方仓库明确将模型和推理代码限制在学术研究、个人学习与其他非商业用途；商业用途请先取得官方许可。

官方入口：

- [JarvisArt 官方仓库](https://github.com/LYL1015/JarvisArt)
- [JarvisArt 官方模型页](https://huggingface.co/JarvisArt/JarvisArt-1208)
- [官方批量推理说明](https://github.com/LYL1015/JarvisArt/blob/main/docs/README_Inference.md)

### 5.1 先理解两种“官方使用方式”

1. **官方 Basic Inference（最容易验证）**：生成 `output_image.lrtemplate`，然后由你手动导入 Lightroom Classic。这是官方批量推理文档明确给出的模式。
2. **AI Lightroom 的 JarvisArt Local GGUF**：连接一个已经在本机运行、并满足本应用本地桥接协议的 GGUF / llama.cpp 服务。它能把返回的 Lightroom 参数安全映射为当前应用的 `EditingPlan`。这不是“把模型路径直接填到软件里”就能完成的功能。

官方批量推理文档中用于 Basic Inference 的权重目录是 `JarvisArt-preview`；`JarvisArt-1208` 是另一个官方模型页面。请以官方仓库当前的推理配置和许可证为准，不要把第三方量化权重冒充为官方权重。

### 5.2 官方 Basic Inference 的下载步骤

以下步骤用于独立生成 Lightroom 预设，并不把模型塞进 AI Lightroom。建议使用有足够显存与磁盘空间的机器；官方推理配置默认面向 CUDA 服务器环境。Windows 用户也可以在 PowerShell 中执行相同的 Conda 命令，但若某个依赖没有 Windows 轮子，请遵循官方仓库的环境要求或改用 WSL/Linux。

```powershell
git clone https://github.com/LYL1015/JarvisArt.git
Set-Location JarvisArt
conda create -n jarvisart_infer python=3.11 -y
conda activate jarvisart_infer
conda install -c conda-forge ffmpeg=7 pkg-config -y
pip install -r envs/requirements_demo.txt

# 官方 Basic Inference 文档使用的 preview 权重：
New-Item -ItemType Directory -Force checkpoints/pretrained/JarvisArt-preview
huggingface-cli download JarvisArt/JarvisArt-preview --local-dir checkpoints/pretrained/JarvisArt-preview
```

下载后，核对 `src/inference/config/qwen2_vl.yaml` 中 `model_name_or_path` 是否正好指向上述目录。启动官方 API 服务时，在新 PowerShell 窗口运行：

```powershell
$env:API_PORT = '8002'
$env:CUDA_VISIBLE_DEVICES = '0'
llamafactory-cli api src/inference/config/qwen2_vl.yaml
```

再准备下列目录（每张照片一个子目录）：

```text
你的输入目录/
└─ road/
   ├─ before.jpg
   └─ user_want.txt
```

`user_want.txt` 中写你的修图要求。保持 API 服务运行，在另一个窗口执行：

```powershell
python inference.py --image_path 你的输入目录
```

成功后同目录会出现 `output_image.lrtemplate`。在 Lightroom Classic 中依次选择 **Develop（修改照片）→ Presets（预设）面板的加号 → Import Presets（导入预设）**，选择这个 `.lrtemplate`，然后把预设应用到对应照片。

> 模型页也展示了 Transformers、vLLM 和 SGLang 的通用加载示例，但“能加载视觉模型”不等于一定能得到 JarvisArt 官方 Lightroom 操作格式。要验证 JarvisArt 的调色输出，请优先遵循官方仓库的 `inference.py`、配置和后处理流程。

### 5.3 把已存在的本地 JarvisArt 服务接入 AI Lightroom

在软件中选择 **文件 → 设置 → AI → JarvisArt Local GGUF → Local GGUF**。填写本地服务根目录和 Endpoint，然后点击 **启动 JarvisArt**。默认 Endpoint 为 `http://127.0.0.1:8765`。你的 GGUF、视觉投影文件与运行时留在本机；本应用只通过 localhost 调用。

本应用只接受一个明确的本地桥接协议：

- `GET /health` 返回对象，且就绪状态至少包含 `status: "ok"` 和 `model_status: "online"`。
- `POST /develop_settings` 接收临时 `photo_path` 与 `prompt`，返回可解析的 Lightroom Lua 标量参数。

运行中的本地服务只有符合这两个接口时，才会显示 **Ready**。AI Lightroom 会把缩小预览写进临时文件，通过 `127.0.0.1` 交给本地服务，并在请求结束后删除临时文件；不会上传原始照片，也不计入云端 AI 费用。

如果你只有官方的 `8002` API、没有这个本地桥接层，请先使用 5.2 的官方 Basic Inference 生成 `.lrtemplate`，不要把 `8002` 直接填成 `8765` 后期待软件自动转换协议。当前版本不会假装这种连接已经成功。

更详细的连接状态与故障处理见 [JarvisArt 本地部署与连接说明](JARVISART_zh-CN.md)。

## 6. 常用快捷键

| 快捷键 | 作用 |
| --- | --- |
| `Ctrl+O` | 打开图片 |
| `Ctrl+S` / `Ctrl+Shift+S` | 导出 / 导出为 |
| `Ctrl+Z` | 撤回 |
| `Ctrl+Y` 或 `Ctrl+Shift+Z` | 重做 |
| `\` 或按住 **原图对比** | 查看原图 |
| `F` / `1` | 适合窗口 / 100% |
| `Ctrl+Enter` | 发送 AI 请求 |
| `Enter` | AI 输入框换行 |

## 7. 需要帮助时先做这三件事

1. 确认正在使用的 Provider、模型名和 AI 面板错误详情。
2. 打开 **帮助 → 打开日志文件夹**，只分享已脱敏的诊断信息；不要分享 API Key、照片或 Windows Credential 内容。
3. 阅读 [故障排除](TROUBLESHOOTING.md)。问题与 JarvisArt 有关时，同时提供它的 `/health` 结果和启动日志中不含隐私的末尾部分。
