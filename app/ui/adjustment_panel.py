from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.core.editor_state import EditorState


@dataclass(frozen=True, slots=True)
class SliderSpec:
    key: str
    label: str
    minimum: int
    maximum: int
    scale: int = 1


BASIC_SPECS = (
    SliderSpec("exposure", "曝光", -500, 500, 100),
    SliderSpec("contrast", "对比度", -100, 100),
    SliderSpec("highlights", "高光", -100, 100),
    SliderSpec("shadows", "阴影", -100, 100),
    SliderSpec("whites", "白色色阶", -100, 100),
    SliderSpec("blacks", "黑色色阶", -100, 100),
    SliderSpec("temperature", "色温", -100, 100),
    SliderSpec("tint", "Tint", -100, 100),
    SliderSpec("saturation", "饱和度", -100, 100),
    SliderSpec("vibrance", "自然饱和度", -100, 100),
    SliderSpec("clarity", "清晰度", -100, 100),
    SliderSpec("texture", "纹理", -100, 100),
    SliderSpec("dehaze", "去朦胧", -100, 100),
    SliderSpec("sharpen", "锐化", 0, 100),
    SliderSpec("vignette", "暗角", -100, 100),
)


class ParameterSlider(QWidget):
    value_changed = Signal(str, float)

    def __init__(self, spec: SliderSpec, parent=None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.label = QLabel(spec.label)
        self.value_label = QLabel("0")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setMinimumWidth(42)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(spec.minimum, spec.maximum)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self._emit_value)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(self.label)
        top.addStretch()
        top.addWidget(self.value_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 4)
        layout.setSpacing(2)
        layout.addLayout(top)
        layout.addWidget(self.slider)

    def _emit_value(self, raw: int) -> None:
        value = raw / self.spec.scale
        self.value_label.setText(f"{value:+.2f}" if self.spec.scale != 1 else f"{value:+.0f}")
        self.value_changed.emit(self.spec.key, value)

    def set_value(self, value: float) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(round(value * self.spec.scale))
        self.slider.blockSignals(False)
        self._update_label(value)

    def _update_label(self, value: float) -> None:
        self.value_label.setText(f"{value:+.2f}" if self.spec.scale != 1 else f"{value:+.0f}")


class AdjustmentPanel(QScrollArea):
    adjustment_changed = Signal(str, float)
    reset_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("编辑")
        title.setStyleSheet("font-size: 13pt; font-weight: 600;")
        reset = QPushButton("重置")
        reset.clicked.connect(self.reset_requested)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(reset)
        layout.addLayout(header)

        basic = QGroupBox("基础调整")
        basic_layout = QVBoxLayout(basic)
        self.controls: dict[str, ParameterSlider] = {}
        for spec in BASIC_SPECS:
            control = ParameterSlider(spec)
            control.value_changed.connect(self.adjustment_changed)
            self.controls[spec.key] = control
            basic_layout.addWidget(control)
        layout.addWidget(basic)

        for name, note in (
            ("HSL / 颜色", "八色相独立调整"),
            ("曲线", "RGB 与分通道曲线"),
            ("局部调整", "渐变、范围和智能蒙版"),
        ):
            group = QGroupBox(name)
            group_layout = QFormLayout(group)
            muted = QLabel(note)
            muted.setStyleSheet("color: #858b92;")
            group_layout.addRow(muted)
            layout.addWidget(group)
        layout.addStretch()
        self.setWidget(container)

    def set_enabled_for_image(self, enabled: bool) -> None:
        self.widget().setEnabled(enabled)

    def set_state(self, state: EditorState) -> None:
        for key, control in self.controls.items():
            control.set_value(getattr(state.basic, key))
