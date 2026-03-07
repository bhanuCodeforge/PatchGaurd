import functools
import logging
from typing import Any, Callable

def trace(func: Callable) -> Callable:
    """Decorator to log function entry and exit with class and function names."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = logging.getLogger(func.__module__)
        
        # Try to identify class name for methods
        cls_name = ""
        if args and hasattr(args[0], '__class__'):
            # This handles both instance methods (self) and class methods (cls)
            cls_name = f"{args[0].__class__.__name__}."
        
        func_name = f"{cls_name}{func.__name__}"
        
        logger.info(f"ENTER: {func_name}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"EXIT: {func_name}")
            return result
        except Exception as e:
            logger.error(f"EXIT (ERROR): {func_name} - {e}")
            raise
    return wrapper
