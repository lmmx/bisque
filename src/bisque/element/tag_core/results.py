from __future__ import annotations

__all__ = ["BaseResultSet"]


class BaseResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""

    def __init__(self, source, result=()):
        """Constructor.

        :param source: A SoupStrainer.
        :param result: A list of PageElements.
        """
        super().__init__(result)
        self.source = source

    def __getattr__(self, key):
        """Raise a helpful exception to explain a common code fix."""
        raise AttributeError(
            f"ResultSet object has no attribute {key!r}. You're probably treating a list of elements like a single element. Did you call find_all() when you meant to call find()?",
        )
