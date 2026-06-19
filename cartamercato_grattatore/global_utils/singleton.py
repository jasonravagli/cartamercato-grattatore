from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


def singleton[T](cls: type[T]) -> Callable[..., T]:
    """Decorator to make a class a singleton."""
    instances = {}

    def get_instance(*args: Any, **kwargs: Any) -> T:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
