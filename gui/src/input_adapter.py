"""Input adapter for relaying Raspberry Pi touch/gesture data into the GUI.

The adapter listens for JSON messages sent over UDP from the Pi (or a
companion touch microservice). Each datagram should be a JSON object that
includes a ``type`` field (for example, ``"gesture"`` or ``"footswitch"``)
along with any supporting metadata. Example payloads::

    {"type": "gesture", "gesture": "swipe_left"}
    {"type": "gesture", "gesture": "tap"}
    {"type": "footswitch", "slot": 0}

Signals are emitted back to the Qt main thread to keep GUI interactions
thread-safe.
"""

from __future__ import annotations

import json
import os
import select
import socket
import threading
import time
from typing import Dict, Tuple

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from utils import config_dir

INPUT_SETTINGS_PATH = os.path.join(config_dir, "input_settings.json")


def load_input_settings() -> dict:
    """Load calibration/configuration settings for Pi input events.

    If the configuration file is missing, a default one is generated to give
    callers a stable contract for screen calibration, orientation, and preset
    metadata used by the adapter.
    """

    defaults = {
        "network": {"host": "0.0.0.0", "port": 57575, "debounce_ms": 120},
        "screen": {"width": 480, "height": 800, "orientation": "portrait"},
        "presets": {"default": ["Default"]},
    }

    os.makedirs(config_dir, exist_ok=True)
    if not os.path.exists(INPUT_SETTINGS_PATH):
        with open(INPUT_SETTINGS_PATH, "w", encoding="utf-8") as handle:
            json.dump(defaults, handle, indent=2)
        return defaults

    try:
        with open(INPUT_SETTINGS_PATH, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
            # Merge to ensure required keys exist even if file is partially
            # configured.
            merged = defaults.copy()
            merged.update(loaded)
            return merged
    except (json.JSONDecodeError, OSError):
        return defaults


class _PiInputListener(QThread):
    """Background listener thread for UDP messages from the Pi.

    Debouncing is handled by ignoring repeated event *types* within
    ``debounce_ms`` milliseconds.
    """

    messageReceived = pyqtSignal(dict)
    statusChanged = pyqtSignal(str, str)  # message, level

    def __init__(self, host: str, port: int, debounce_ms: int):
        super().__init__()
        self.host = host
        self.port = port
        self.debounce_ms = debounce_ms
        self._running = threading.Event()
        self._running.set()
        self._last_events: Dict[str, float] = {}

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self.host, self.port))
            sock.setblocking(False)
            self.statusChanged.emit(
                f"Listening for Pi input on udp://{self.host}:{self.port}",
                "info",
            )
        except OSError as exc:
            self.statusChanged.emit(f"Failed to bind UDP socket: {exc}", "error")
            return

        while self._running.is_set():
            readable, _, _ = select.select([sock], [], [], 0.25)
            if not readable:
                continue
            try:
                packet, _ = sock.recvfrom(4096)
            except OSError:
                self.statusChanged.emit("Socket closed unexpectedly", "error")
                break

            now = time.time() * 1000
            try:
                payload = json.loads(packet.decode("utf-8"))
            except json.JSONDecodeError:
                self.statusChanged.emit("Dropped malformed JSON input", "warn")
                continue

            event_type = payload.get("type", "unknown")
            last = self._last_events.get(event_type, 0)
            if now - last < self.debounce_ms:
                continue
            self._last_events[event_type] = now
            self.messageReceived.emit(payload)

        sock.close()
        self.statusChanged.emit("Stopped listening for Pi input", "info")

    def stop(self):
        self._running.clear()


class PiInputAdapter(QObject):
    """Translates Pi touch/gesture payloads into GUI actions.

    The adapter lives outside the GUI thread; it emits Qt signals for both
    actionable events and status updates so that widgets can marshal the work
    back into the main loop safely.
    """

    actionTriggered = pyqtSignal(str, dict)
    statusChanged = pyqtSignal(str, str)

    def __init__(self, settings: dict):
        super().__init__()
        network = settings.get("network", {})
        self.screen_config: Tuple[int, int, str] = (
            settings.get("screen", {}).get("width", 480),
            settings.get("screen", {}).get("height", 800),
            settings.get("screen", {}).get("orientation", "portrait"),
        )
        self.listener = _PiInputListener(
            network.get("host", "0.0.0.0"),
            int(network.get("port", 57575)),
            int(network.get("debounce_ms", 120)),
        )
        self.listener.messageReceived.connect(self._handle_message)
        self.listener.statusChanged.connect(self.statusChanged.emit)

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()
        self.listener.wait(500)

    def _handle_message(self, payload: dict):
        payload_type = payload.get("type")
        if payload_type == "gesture":
            gesture = payload.get("gesture")
            if gesture in {"swipe_left", "profile_prev"}:
                self.actionTriggered.emit("profile_prev", payload)
            elif gesture in {"swipe_right", "profile_next"}:
                self.actionTriggered.emit("profile_next", payload)
            elif gesture in {"tap", "profile_select"}:
                self.actionTriggered.emit("profile_select", payload)
            elif gesture in {"preset_next", "swipe_up"}:
                self.actionTriggered.emit("preset_next", payload)
            elif gesture in {"preset_prev", "swipe_down"}:
                self.actionTriggered.emit("preset_prev", payload)
            else:
                self.statusChanged.emit(
                    f"Unhandled gesture '{gesture}'", "warn"
                )
        elif payload_type == "footswitch":
            self.actionTriggered.emit("footswitch", payload)
        else:
            self.statusChanged.emit(
                f"Ignored payload with unknown type '{payload_type}'", "warn"
            )
