"""
Fast Lane Collector — lightweight performance metrics (every ~5 seconds).

Cross-platform: Windows · Linux/Ubuntu · macOS
Uses only psutil for zero subprocess overhead.
"""

import platform
import time
import logging
from typing import Dict, Any

import psutil

logger = logging.getLogger("PatchAgent.FastLane")

OS = platform.system()  # "Windows" | "Linux" | "Darwin"


class FastLaneCollector:
    """
    Collects lightweight, real-time performance metrics.

    Metrics:
      - cpu_percent          (float, 0-100)
      - memory_percent       (float, 0-100)
      - memory_used_bytes    (int)
      - memory_total_bytes   (int)
      - disk_usage_percent   (float, 0-100)
      - disk_read_bytes_sec  (float)
      - disk_write_bytes_sec (float)
      - net_sent_bytes_sec   (float)
      - net_recv_bytes_sec   (float)
      - process_count        (int)
      - timestamp            (float, epoch)
    """

    def __init__(self):
        # Snapshots for delta-based I/O rates
        self._last_disk_io = psutil.disk_io_counters()
        self._last_net_io = psutil.net_io_counters()
        self._last_ts = time.monotonic()

        # Prime CPU percent (first call always returns 0)
        psutil.cpu_percent(interval=None)

    def collect(self) -> Dict[str, Any]:
        """Return a dict of current performance metrics."""
        now = time.monotonic()
        elapsed = max(now - self._last_ts, 0.1)

        # CPU (non-blocking, uses delta since last call)
        cpu_pct = psutil.cpu_percent(interval=None)

        # Memory
        mem = psutil.virtual_memory()

        # Disk usage (root / C:\)
        disk_path = "C:\\" if OS == "Windows" else "/"
        try:
            disk = psutil.disk_usage(disk_path)
            disk_pct = disk.percent
        except Exception:
            disk_pct = 0.0

        # Disk I/O rates
        try:
            dio = psutil.disk_io_counters()
            if dio and self._last_disk_io:
                read_rate = (dio.read_bytes - self._last_disk_io.read_bytes) / elapsed
                write_rate = (dio.write_bytes - self._last_disk_io.write_bytes) / elapsed
            else:
                read_rate = write_rate = 0.0
            self._last_disk_io = dio
        except Exception:
            read_rate = write_rate = 0.0

        # Network I/O rates
        try:
            nio = psutil.net_io_counters()
            if nio and self._last_net_io:
                sent_rate = (nio.bytes_sent - self._last_net_io.bytes_sent) / elapsed
                recv_rate = (nio.bytes_recv - self._last_net_io.bytes_recv) / elapsed
            else:
                sent_rate = recv_rate = 0.0
            self._last_net_io = nio
        except Exception:
            sent_rate = recv_rate = 0.0

        self._last_ts = now

        # Per-CPU breakdown (optional, useful for multi-core graphs)
        per_cpu = psutil.cpu_percent(interval=None, percpu=True)

        return {
            "cpu_percent": round(cpu_pct, 1),
            "cpu_per_core": [round(c, 1) for c in per_cpu],
            "memory_percent": round(mem.percent, 1),
            "memory_used_bytes": mem.used,
            "memory_total_bytes": mem.total,
            "disk_usage_percent": round(disk_pct, 1),
            "disk_read_bytes_sec": round(read_rate, 0),
            "disk_write_bytes_sec": round(write_rate, 0),
            "net_sent_bytes_sec": round(sent_rate, 0),
            "net_recv_bytes_sec": round(recv_rate, 0),
            "process_count": len(psutil.pids()),
            "timestamp": time.time(),
        }
