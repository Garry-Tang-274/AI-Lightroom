# 故障排除

[English](TROUBLESHOOTING.md)

## 程序能打开，但 AI 不可用

手动修图不需要 Provider。请在设置中配置云端 Key，或选择 JarvisArt Local GGUF。查看 AI 面板状态中的当前 Provider 和模型。Offline Mock 被故意禁止用于真实调色，因为它不会分析照片。

## 云端连接测试失败

检查 Key、Model ID、Endpoint、网络、额度和你声明的能力。错误详情会显示安全的 HTTP/Provider 信息，但不会显示 Key。普通请求不会自动重试。

## JarvisArt Local GGUF 显示 Offline

选择 **JarvisArt Local GGUF → Local GGUF**。若自动检测没有找到它，填写本地运行时根目录；确认启动器、GGUF 与视觉投影文件已安装后，点击 **启动 JarvisArt**。不要把模型文件路径直接填入 AI Lightroom；软件需要一个现成的 localhost bridge。

本地 bridge 与上游官方 API 的端口和请求格式可能不同。修改 Endpoint 前，请阅读 [JarvisArt Local GGUF](JARVISART_zh-CN.md)。

## 渲染或导出失败

选择 **帮助 → 打开日志文件夹**，只分享已脱敏的诊断信息。检查导出文件夹的写入权限和磁盘空间。
