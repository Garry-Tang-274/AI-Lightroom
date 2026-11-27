"""Compare the current renderer with a trusted Git revision or Python file.

Run from the repository root with its existing virtual environment. No images,
network requests, UI windows, or additional dependencies are required.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from app.core import image_processor as current
from app.core.editor_state import (
    CurvePoint, EditorState, HSLAdjustment, HSLColor, LocalAdjustments,
    MaskLayer, MaskType, ToneCurve,
)


def positive_int(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return result


def load_baseline(reference: str, path: Path | None) -> ModuleType:
    if path is not None:
        filename = str(path.resolve())
        source = path.read_text(encoding="utf-8-sig")
    else:
        filename = f"{reference}:app/core/image_processor.py"
        source = subprocess.run(
            ["git", "show", "--no-ext-diff", "--end-of-options", filename],
            cwd=ROOT, check=True, capture_output=True, encoding="utf-8",
        ).stdout
    module = ModuleType("renderer_benchmark_baseline")
    module.__file__ = filename
    exec(compile(source, filename, "exec"), module.__dict__)
    return module


def make_state(case: str) -> EditorState:
    state = EditorState()
    state.basic.contrast = 12
    if case != "contrast":
        state.basic.exposure = 0.25
        state.basic.highlights = -20
        state.basic.clarity = 8
    if case in {"hsl", "heavy"}:
        state.hsl[HSLColor.BLUE] = HSLAdjustment(saturation=-10, luminance=-5)
    if case == "heavy":
        state.basic.dehaze = 8
        state.curves.rgb = ToneCurve(points=[
            CurvePoint(x=0, y=0), CurvePoint(x=0.2, y=0.14),
            CurvePoint(x=0.75, y=0.81), CurvePoint(x=1, y=1),
        ])
        for index, color in enumerate(HSLColor):
            state.hsl[color] = HSLAdjustment(
                hue=(index - 3) * 3, saturation=(index - 4) * 4,
                luminance=(index - 2) * 2,
            )
        state.masks = [MaskLayer(
            name="Benchmark", type=MaskType.RADIAL_GRADIENT,
            adjustments=LocalAdjustments(exposure=-0.3, clarity=8, saturation=-5),
        )]
    return state


def measure(baseline: ModuleType, edge: int, case: str, repeats: int) -> dict:
    source = np.random.default_rng(7).integers(
        0, 256, (max(1, edge * 2 // 3), edge, 3), dtype=np.uint8,
    )
    state = make_state(case)
    # The output comparison also warms each implementation once.
    before = baseline.render_image(source, state)
    after = current.render_image(source, state)
    delta = np.abs(before.astype(np.int16) - after.astype(np.int16))
    times = {"before": [], "after": []}
    order = [("before", baseline), ("after", current)]
    for index in range(repeats):
        for label, module in order if index % 2 == 0 else reversed(order):
            start = time.perf_counter()
            module.render_image(source, state)
            times[label].append((time.perf_counter() - start) * 1000)
    return {
        "edge": edge, "case": case,
        "before_ms": round(statistics.median(times["before"]), 2),
        "after_ms": round(statistics.median(times["after"]), 2),
        "max_channel_delta": int(delta.max()),
        "changed_channels_percent": float(np.count_nonzero(delta) / delta.size * 100),
        "mean_channel_delta": float(delta.mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    baseline = parser.add_mutually_exclusive_group()
    baseline.add_argument("--baseline-ref", default="e7f6b85", help="trusted Git revision (default: e7f6b85)")
    baseline.add_argument("--baseline-file", type=Path, help="trusted image_processor.py file instead of Git")
    parser.add_argument("--edges", nargs="+", type=positive_int, default=[1280, 1536, 3072])
    parser.add_argument("--cases", nargs="+", choices=["contrast", "basic", "hsl", "heavy"],
                        default=["contrast", "basic", "hsl", "heavy"])
    parser.add_argument("--repeats", type=positive_int, default=5)
    parser.add_argument("--output", type=Path, help="optional JSON output; prefer the ignored temp/ directory")
    args = parser.parse_args()
    old = load_baseline(args.baseline_ref, args.baseline_file)
    rows = []
    for edge in args.edges:
        for case in args.cases:
            row = measure(old, edge, case, args.repeats)
            rows.append(row)
            print(json.dumps(row), flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result = {
            "baseline": str(args.baseline_file or args.baseline_ref),
            "platform": platform.platform(), "python": platform.python_version(),
            "numpy": np.__version__, "opencv": cv2.__version__,
            "opencv_threads": cv2.getNumThreads(), "repeats": args.repeats,
            "seed": 7, "rows": rows,
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
