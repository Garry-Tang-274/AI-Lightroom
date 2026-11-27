# Renderer v1.2 benchmark / v1.2 渲染性能实测

The v1.2 renderer reduces full-image temporary allocations, uses a native float32 luminance pass, skips unused tonal calculations for contrast-only edits, and processes HSL in contiguous channels. The editing equations and full-resolution export path remain unchanged.

v1.2 减少整图临时数组，通过原生 float32 运算计算亮度，纯对比度编辑跳过无用的分区亮度计算，并使用连续通道处理 HSL。调色公式和全分辨率导出路径保持不变。

## Measured results / 实测结果

Baseline: `e7f6b85` renderer; candidate: v1.2 renderer. Windows 11 build 26200, Intel Core Ultra 9 275HX, Python 3.12.10, NumPy 2.5.1, OpenCV 4.14.0, 24 OpenCV threads. This benchmark exercises the CPU renderer, not AI inference or end-to-end UI latency.

基线为 `e7f6b85` 的渲染器，对照为 v1.2 渲染器。环境：Windows 11 build 26200、Intel Core Ultra 9 275HX、Python 3.12.10、NumPy 2.5.1、OpenCV 4.14.0、OpenCV 24 线程。测量的是 CPU 渲染时间，不包含 AI 推理或界面端到端延迟。

Times are paired-run medians in milliseconds; lower is better. The process generates a 3:2 RGB uint8 noise image using `default_rng(7)`, warms both implementations once, then alternates their execution order for five runs each. Background load affects absolute timings.

下表为配对运行的中位数，单位毫秒，越低越好。使用 `default_rng(7)` 生成 3:2 的 RGB uint8 随机图，新旧实现各预热一次，之后交替先后顺序各运行五次。后台负载会影响绝对耗时。

| Long edge / 长边 | Case / 编辑案例 | Before / 原版 ms | After / 新版 ms |
|---:|---|---:|---:|
| 1280 | Contrast / 对比度 | 58.63 | 30.74 |
| 1280 | Basic / 基础 | 198.46 | 157.54 |
| 1280 | HSL / 色彩 | 183.44 | 150.28 |
| 1280 | Heavy / 重编辑 | 948.78 | 744.67 |
| 1536 | Contrast / 对比度 | 71.51 | 37.13 |
| 1536 | Basic / 基础 | 228.62 | 181.51 |
| 1536 | HSL / 色彩 | 247.81 | 207.22 |
| 1536 | Heavy / 重编辑 | 1063.06 | 863.26 |
| 3072 | Contrast / 对比度 | 224.49 | 123.88 |
| 3072 | Basic / 基础 | 890.09 | 756.27 |
| 3072 | HSL / 色彩 | 1007.66 | 825.61 |
| 3072 | Heavy / 重编辑 | 4166.25 | 3262.25 |

- **Contrast / 对比度:** contrast / 对比度 `+12`.
- **Basic / 基础:** contrast / 对比度 `+12`, exposure / 曝光 `+0.25`, highlights / 高光 `−20`, clarity / 清晰度 `+8`.
- **HSL / 色彩:** Basic + blue saturation / 基础加蓝色饱和度 `−10`, blue luminance / 蓝色明亮度 `−5`.
- **Heavy / 重编辑:** Basic + dehaze `+8`, four-point RGB curve, eight HSL ranges and a radial exposure/clarity/saturation mask; exact values are in `make_state()` below. / 基础加去雾 `+8`、四点 RGB 曲线、八色 HSL 和径向曝光/清晰度/饱和度蒙版；精确参数见下方脚本的 `make_state()`。

Contrast, Basic and HSL outputs were pixel-identical at all three sizes. Heavy differed by at most one 8-bit channel level, affecting at most **0.000106% of channels**, due to float32 rounding in equivalent circular hue-distance arithmetic. The optimized renderer passed 51 existing core tests and six added regression cases. High-resolution heavy editing still takes seconds; these results do not imply real-time full-resolution rendering.

对比度、基础和单色 HSL 在三个尺寸下均逐像素相同。重编辑最大相差一个 8 位通道等级，最多影响 **0.000106% 的通道**，来自等价色相圆周距离运算的 float32 舍入。优化后通过原有 51 项核心测试和新增 6 项回归测试。高分辨率重编辑仍需数秒，不代表全分辨率实时渲染。

## Reproduce / 复现

From the repository root, with the existing development dependencies installed:

在仓库根目录，使用已经安装开发依赖的虚拟环境执行：

```powershell
.venv\Scripts\python.exe docs\benchmarks\render_v1_2.py --output temp\render-benchmark.json
```

The script reads only `app/core/image_processor.py` from Git revision `e7f6b85`; supporting modules come from the current checkout for both implementations. It compares that renderer with the current working-tree renderer, so later renderer edits will produce different candidate results. No user photographs, network calls, or GUI windows are used.

脚本仅从 Git 提交 `e7f6b85` 读取 `app/core/image_processor.py`；新旧实现都使用当前工作区的配套模块。对照对象是当前工作区渲染器，因此后续修改渲染器后会得到新的候选结果。脚本不使用用户照片，不调用网络，也不打开界面。

A small entry-point check (not a performance measurement):

最小入口验证（不是性能测量）：

```powershell
.venv\Scripts\python.exe docs\benchmarks\render_v1_2.py --edges 64 --cases contrast hsl heavy --repeats 1
```

For a source archive without Git history, supply an existing trusted baseline file. Both baseline options execute Python code; use project-owned code only.

没有 Git 历史的源码包可以指定已有的可信基线文件。两种基线方式都会执行 Python 代码，仅使用可信项目代码。

```powershell
.venv\Scripts\python.exe docs\benchmarks\render_v1_2.py --baseline-file C:\path\to\image_processor.py --output temp\render-benchmark.json
```
