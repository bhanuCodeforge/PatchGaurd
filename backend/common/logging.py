"""Logging utilities shared across the backend."""
import asyncio
import functools
import logging
from typing import Any, Callable


def trace(func: Callable) -> Callable:
    """
    Decorator that logs entry/exit for both sync and async functions.

    Async-aware: correctly awaits coroutine functions instead of returning
    a coroutine object from a sync wrapper.
    """
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = logging.getLogger(func.__module__)
        cls_name = ""
        if args and hasattr(args[0], "__class__"):
            cls_name = f"{args[0].__class__.__name__}."
        func_name = f"{cls_name}{func.__name__}"
        logger.debug("ENTER: %s", func_name)
        try:
            result = await func(*args, **kwargs)
            logger.debug("EXIT: %s", func_name)
            return result
        except Exception as e:
            logger.error("EXIT (ERROR): %s — %s", func_name, e)
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = logging.getLogger(func.__module__)
        cls_name = ""
        if args and hasattr(args[0], "__class__"):
            cls_name = f"{args[0].__class__.__name__}."
        func_name = f"{cls_name}{func.__name__}"
        logger.debug("ENTER: %s", func_name)
        try:
            result = func(*args, **kwargs)
            logger.debug("EXIT: %s", func_name)
            return result
        except Exception as e:
            logger.error("EXIT (ERROR): %s — %s", func_name, e)
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
