# Third-party notices

AI Lightroom source is MIT-licensed. Its Windows distribution bundles or depends on third-party components under their own terms.

| Component | License / terms | Use in AI Lightroom |
| --- | --- | --- |
| PySide6 / Qt | LGPL-3.0 or GPL alternatives | Dynamic Qt Python bindings; retain applicable Qt/PySide notices when redistributing. |
| OpenCV | Apache-2.0 | Image operations and mask analysis. |
| Pillow | HPND-style license | Image I/O and metadata. |
| NumPy | BSD-style | Array processing. |
| SciPy / OpenBLAS | BSD-style; binary notices apply | Optional numerical helpers. |
| Pydantic | MIT | Schema validation. |
| python-dotenv | BSD-3-Clause | Optional local environment configuration. |
| google-genai | Apache-2.0 | Optional Gemini client. |
| OpenAI Python | Apache-2.0 | Optional OpenAI-compatible clients. |
| psutil | BSD-3-Clause | Local diagnostics/service ownership. |
| PyInstaller | GPL-2.0-or-later with its distribution exception | Windows packaging tool. |

Package metadata was reviewed in the release environment on 2026-08-09. This table is a notice summary, not legal advice. Release builders should retain the notices shipped with their installed dependencies, especially Qt/PySide and binary numerical libraries.

## JarvisArt

JarvisArt code, model weights, and licenses are **not** included in this repository or release. JarvisArt is an independently installed optional component and remains under its own license (including any non-commercial terms). AI Lightroom supplies only a localhost provider adapter.
