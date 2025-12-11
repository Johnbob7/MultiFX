"""Utility functions for gathering runtime debug information."""

import os
import time
from typing import Dict, Iterable, Optional


def _read_first_float(paths: Iterable[str], scale: Optional[float] = None) -> Optional[float]:
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw_value = handle.read().strip()
                if raw_value == "":
                    continue
                value = float(raw_value)
                if scale:
                    value /= scale
                return value
        except (FileNotFoundError, OSError, ValueError):
            continue
    return None


def read_cpu_temperature() -> Optional[float]:
    """Return CPU temperature in Celsius if available."""
    thermal_paths = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/hwmon/hwmon0/temp1_input",
    ]
    temp = _read_first_float(thermal_paths, scale=1000)
    return temp


def read_cpu_frequency() -> Optional[float]:
    """Return CPU frequency in GHz if available."""
    freq_paths = [
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq",
        "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq",
    ]
    freq_hz = _read_first_float(freq_paths)
    if freq_hz is None:
        return None
    return freq_hz / 1_000_000  # to GHz


def read_power_usage() -> Optional[float]:
    """Return power usage in Watts if available."""
    power_paths = [
        "/sys/class/power_supply/BAT0/power_now",
        "/sys/class/power_supply/AC/power_now",
        "/sys/class/power_supply/usb/typec/power_now",
    ]
    power_watts = _read_first_float(power_paths, scale=1_000_000)
    if power_watts is not None:
        return power_watts

    current = _read_first_float(
        (
            "/sys/class/power_supply/BAT0/current_now",
            "/sys/class/power_supply/AC/current_now",
            "/sys/class/power_supply/usb/typec/current_now",
        ),
        scale=1_000_000,
    )
    voltage = _read_first_float(
        (
            "/sys/class/power_supply/BAT0/voltage_now",
            "/sys/class/power_supply/AC/voltage_now",
            "/sys/class/power_supply/usb/typec/voltage_now",
        ),
        scale=1_000_000,
    )
    if current is not None and voltage is not None:
        return current * voltage
    return None


def read_memory_usage() -> Optional[tuple[float, float]]:
    """Return used and total memory in GB if available."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            meminfo = handle.read().splitlines()
    except (FileNotFoundError, OSError):
        return None

    values: Dict[str, int] = {}
    for line in meminfo:
        parts = line.split(":")
        if len(parts) != 2:
            continue
        key, value = parts
        try:
            values[key.strip()] = int(value.strip().split()[0])
        except ValueError:
            continue

    total_kb = values.get("MemTotal")
    available_kb = values.get("MemAvailable")
    if total_kb is None or available_kb is None:
        return None

    used_kb = total_kb - available_kb
    return used_kb / 1_048_576, total_kb / 1_048_576  # to GB


def read_load_average() -> Optional[tuple[float, float, float]]:
    try:
        return os.getloadavg()
    except (OSError, AttributeError):
        return None


def read_uptime() -> Optional[float]:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as handle:
            uptime_seconds = float(handle.read().split()[0])
        return uptime_seconds
    except (FileNotFoundError, OSError, ValueError):
        return None


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def collect_debug_metrics() -> Dict[str, str]:
    metrics: Dict[str, str] = {}

    if (power := read_power_usage()) is not None:
        metrics["Power Draw"] = f"{power:.2f} W"
    else:
        metrics["Power Draw"] = "n/a"

    if (temp := read_cpu_temperature()) is not None:
        metrics["CPU Temp"] = f"{temp:.1f} °C"
    else:
        metrics["CPU Temp"] = "n/a"

    if (freq := read_cpu_frequency()) is not None:
        metrics["CPU Freq"] = f"{freq:.2f} GHz"
    else:
        metrics["CPU Freq"] = "n/a"

    if (load := read_load_average()) is not None:
        metrics["Load Avg"] = ", ".join(f"{value:.2f}" for value in load)
    else:
        metrics["Load Avg"] = "n/a"

    if (memory := read_memory_usage()) is not None:
        used, total = memory
        metrics["Memory"] = f"{used:.2f} / {total:.2f} GB"
    else:
        metrics["Memory"] = "n/a"

    if (uptime := read_uptime()) is not None:
        metrics["Uptime"] = format_duration(uptime)
    else:
        metrics["Uptime"] = "n/a"

    metrics["Timestamp"] = time.strftime("%H:%M:%S")
    return metrics
