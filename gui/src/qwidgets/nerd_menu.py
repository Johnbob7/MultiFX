"""A lightweight overlay for displaying debug-friendly runtime information."""

from typing import Callable, Dict

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QLabel, QWidget

from qwidgets.graphics_utils import SCREEN_H, SCREEN_W
from styles import styles_label, styles_sublabel, styles_vallabel, styles_window
from system_info import collect_debug_metrics


class NerdMenu(QWidget):
    """Overlay that can be toggled for quick runtime diagnostics."""

    def __init__(self, close_callback: Callable[[], None],
                 context_provider: Callable[[], Dict[str, str]] | None = None):
        super().__init__()
        self.close_callback = close_callback
        self.context_provider = context_provider or (lambda: {})
        self.setGeometry(0, 0, SCREEN_W, SCREEN_H)
        self.setStyleSheet(styles_window)
        self.setFocusPolicy(Qt.StrongFocus)

        self.labels: Dict[str, QLabel] = {}
        self._init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(1000)

    def _init_ui(self):
        self.title = QLabel("NERD MENU", self)
        self.title.setStyleSheet(styles_label)
        self.title.adjustSize()
        self.title.move(
            (self.width() - self.title.width()) // 2,
            int(self.height() * 0.08),
        )

        self.hint = QLabel("Press N to close", self)
        self.hint.setStyleSheet(styles_sublabel)
        self.hint.adjustSize()
        self.hint.move(
            (self.width() - self.hint.width()) // 2,
            self.title.y() + self.title.height() + 10,
        )

        start_y = self.hint.y() + self.hint.height() + 20
        row_height = 44
        for index, field in enumerate(self._fields()):
            label = QLabel(field, self)
            label.setStyleSheet(styles_sublabel)
            label.adjustSize()
            label.move(24, start_y + index * row_height)

            value = QLabel("--", self)
            value.setStyleSheet(styles_vallabel)
            value.adjustSize()
            value.move(int(self.width() * 0.55), start_y + index * row_height)

            self.labels[field] = value

        self.update_metrics()

    def _fields(self):
        return [
            "Power Draw",
            "CPU Temp",
            "CPU Freq",
            "Load Avg",
            "Memory",
            "Uptime",
            "Active Profile",
            "Plugins Loaded",
            "Timestamp",
        ]

    def update_metrics(self):
        metrics = collect_debug_metrics()
        metrics.update(self.context_provider())
        for field in self._fields():
            if field not in metrics:
                continue
            label = self.labels[field]
            label.setText(metrics[field])
            label.adjustSize()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_N:
            self.close_callback()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        return super().closeEvent(event)
