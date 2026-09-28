"""Read and normalize current host metrics without persisting history."""

from dataclasses import dataclass
import time

import psutil


@dataclass(frozen=True, slots=True)
class SystemStats:
    cpu_percent: float | None
    ram_used_bytes: int | None
    ram_total_bytes: int | None
    ram_percent: float | None
    disk_used_bytes: int | None
    disk_total_bytes: int | None
    disk_percent: float | None
    load_average: tuple[float, float, float] | None
    uptime_seconds: int | None


def _read_or_none(read):
    try:
        return read()
    except (
        AttributeError,
        OSError,
        psutil.Error,
        RuntimeError,
        ValueError,
        NotImplementedError,
    ):
        return None


def read_system_stats(disk_path: str = "/") -> SystemStats:
    """Return a best-effort snapshot; unsupported metrics are represented by None."""
    cpu_percent = _read_or_none(lambda: float(psutil.cpu_percent(interval=0.1)))
    memory = _read_or_none(psutil.virtual_memory)
    disk = _read_or_none(lambda: psutil.disk_usage(disk_path))
    load_average = _read_or_none(psutil.getloadavg)
    boot_time = _read_or_none(psutil.boot_time)

    if memory is None:
        ram_used_bytes = ram_total_bytes = ram_percent = None
    else:
        ram_used_bytes = int(memory.used)
        ram_total_bytes = int(memory.total)
        ram_percent = float(memory.percent)

    if disk is None:
        disk_used_bytes = disk_total_bytes = disk_percent = None
    else:
        disk_used_bytes = int(disk.used)
        disk_total_bytes = int(disk.total)
        disk_percent = float(disk.percent)

    if load_average is not None:
        try:
            normalized_load = tuple(float(value) for value in load_average)
            load_average = normalized_load if len(normalized_load) == 3 else None
        except (TypeError, ValueError):
            load_average = None

    uptime_seconds = (
        max(0, int(time.time() - boot_time)) if boot_time is not None else None
    )

    return SystemStats(
        cpu_percent=cpu_percent,
        ram_used_bytes=ram_used_bytes,
        ram_total_bytes=ram_total_bytes,
        ram_percent=ram_percent,
        disk_used_bytes=disk_used_bytes,
        disk_total_bytes=disk_total_bytes,
        disk_percent=disk_percent,
        load_average=load_average,
        uptime_seconds=uptime_seconds,
    )


def format_bytes(value: int | None) -> str:
    if value is None:
        return "niedostępne"
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return "niedostępne"


def format_uptime(seconds: int | None) -> str:
    if seconds is None:
        return "niedostępne"
    days, remainder = divmod(max(0, seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days} d {hours} godz."
    if hours:
        return f"{hours} godz. {minutes} min"
    return f"{minutes} min"
