from enum import Enum, auto

__all__ = ["DEFAULT_TYPES_SENTINEL", "ElementEvent"]


class DEFAULT_TYPES_SENTINEL:
    """Replaces a plain object."""


class ElementEvent(Enum):
    """Names for the different events yielded by _event_stream."""

    START = auto()
    END = auto()
    EMPTY = auto()
    STRING = auto()
