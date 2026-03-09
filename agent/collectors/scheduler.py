"""
Lane Scheduler — orchestrates Fast Lane and Slow Lane collection loops.

Fast Lane: runs every `fast_interval` seconds (default 5s), sends lightweight
           performance metrics via WebSocket.
Slow Lane: runs every `slow_interval` seconds (default 900s / 15min), runs
           heavy OS-specific collectors in a thread executor, sends results
           via WebSocket.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Coroutine, Dict, Optional

from collectors.fast_lane import FastLaneCollector
from collectors.slow_lane import get_slow_collector

logger = logging.getLogger("PatchAgent.Scheduler")

# Thread pool for slow-lane (blocking subprocess calls)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="slow-lane")


class LaneScheduler:
    """
    Manages two concurrent data-collection loops:

      Fast Lane  →  event: "metrics"        (every ~5s)
      Slow Lane  →  event: "slow_lane_data" (every ~15min)

    Both loops call a user-supplied `send_fn(event, payload)` coroutine
    to push data over the WebSocket.
    """

    def __init__(
        self,
        send_fn: Callable[[str, Dict[str, Any]], Coroutine],
        device_id: str,
        fast_interval: int = 5,
        slow_interval: int = 900,
    ):
        self.send_fn = send_fn
        self.device_id = device_id
        self.fast_interval = fast_interval
        self.slow_interval = slow_interval
        self._running = False

        # Initialise collectors
        self._fast = FastLaneCollector()
        self._slow = get_slow_collector()

    # -------------------------------------------------------------- #
    # Public API                                                       #
    # -------------------------------------------------------------- #

    async def start(self):
        """Launch both lane loops concurrently. Returns when stopped."""
        self._running = True
        logger.info(
            f"Lane scheduler started — fast={self.fast_interval}s, slow={self.slow_interval}s"
        )
        await asyncio.gather(
            self._fast_loop(),
            self._slow_loop(),
            return_exceptions=True,
        )

    def stop(self):
        """Signal both loops to exit."""
        self._running = False

    def update_intervals(self, fast: Optional[int] = None, slow: Optional[int] = None):
        """Dynamically update collection intervals (e.g. from CONFIG_UPDATE)."""
        if fast is not None and fast > 0:
            self.fast_interval = fast
            logger.info(f"Fast lane interval updated to {fast}s")
        if slow is not None and slow > 0:
            self.slow_interval = slow
            logger.info(f"Slow lane interval updated to {slow}s")

    # -------------------------------------------------------------- #
    # Fast Lane loop                                                   #
    # -------------------------------------------------------------- #

    async def _fast_loop(self):
        """Collect and send performance metrics every fast_interval seconds."""
        logger.info("Fast lane loop started")
        while self._running:
            try:
                metrics = self._fast.collect()
                metrics["device_id"] = self.device_id

                await self.send_fn("metrics", metrics)
                logger.debug(
                    f"Fast lane → CPU={metrics['cpu_percent']}% "
                    f"MEM={metrics['memory_percent']}% "
                    f"DISK={metrics['disk_usage_percent']}%"
                )
            except Exception as e:
                logger.warning(f"Fast lane error: {e}")
                # If send fails (connection lost), the outer connect loop
                # will handle reconnection. Break to allow it.
                if not self._running:
                    break

            await asyncio.sleep(self.fast_interval)
        logger.info("Fast lane loop stopped")

    # -------------------------------------------------------------- #
    # Slow Lane loop                                                   #
    # -------------------------------------------------------------- #

    async def _slow_loop(self):
        """
        Run heavy OS-specific collectors in a thread pool every slow_interval.
        The first collection runs after a short initial delay to allow
        the agent to complete its WebSocket handshake first.
        """
        logger.info("Slow lane loop started")
        # Small initial delay so agent finishes its connect handshake + system_info
        await asyncio.sleep(15)

        while self._running:
            try:
                logger.info("Slow lane collection triggered...")
                t0 = time.monotonic()

                # Run blocking collector in thread to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(_executor, self._slow.collect)

                elapsed = round(time.monotonic() - t0, 1)
                logger.info(f"Slow lane collection finished in {elapsed}s")

                payload = {
                    "device_id": self.device_id,
                    "data": data,
                    "collection_time_sec": elapsed,
                    "timestamp": time.time(),
                }

                await self.send_fn("slow_lane_data", payload)

            except Exception as e:
                logger.warning(f"Slow lane error: {e}")
                if not self._running:
                    break

            await asyncio.sleep(self.slow_interval)
        logger.info("Slow lane loop stopped")
