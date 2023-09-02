from __future__ import annotations

import warnings
from collections.abc import Callable

__all__ = ["BaseSoupStrainer"]


class BaseSoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    string).

    This is primarily used to underpin the find_* methods, but you can
    create one yourself and pass it in as `parse_only` to the
    `Bisque` constructor, to parse a subset of a large
    document.
    """

    def __init__(self, name=None, attrs={}, string=None, **kwargs):
        """Constructor.

        The SoupStrainer constructor takes the same arguments passed
        into the find_* methods. See the online documentation for
        detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param string: A filter for a NavigableString with specific text.
        :kwargs: A dictionary of filters on attribute values.
        """
        if string is None and "text" in kwargs:
            string = kwargs.pop("text")
            warnings.warn(
                "The 'text' argument to the SoupStrainer constructor is deprecated. Use 'string' instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        self.name = self._normalize_search_value(name)
        if not isinstance(attrs, dict):
            # Treat a non-dict value for attrs as a search for the 'class'
            # attribute.
            kwargs["class"] = attrs
            attrs = None

        if "class_" in kwargs:
            # Treat class_="foo" as a search for the 'class'
            # attribute, overriding any non-dict value for attrs.
            kwargs["class"] = kwargs["class_"]
            del kwargs["class_"]

        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        normalized_attrs = {}
        for key, value in list(attrs.items()):
            normalized_attrs[key] = self._normalize_search_value(value)

        self.attrs = normalized_attrs
        self.string = self._normalize_search_value(string)

        # DEPRECATED but just in case someone is checking this.
        self.text = self.string

    def _normalize_search_value(self, value):
        # Leave it alone if it's a Unicode string, a callable, a
        # regular expression, a boolean, or None.
        if (
            isinstance(value, str)
            or isinstance(value, Callable)
            or hasattr(value, "match")
            or isinstance(value, bool)
            or value is None
        ):
            return value

        # If it's a bytestring, convert it to Unicode, treating it as UTF-8.
        if isinstance(value, bytes):
            return value.decode("utf8")

        # If it's listlike, convert it into a list of strings.
        if hasattr(value, "__iter__"):
            new_value = []
            for v in value:
                if (
                    hasattr(v, "__iter__")
                    and not isinstance(v, bytes)
                    and not isinstance(v, str)
                ):
                    # This is almost certainly the user's mistake. In the
                    # interests of avoiding infinite loops, we'll let
                    # it through as-is rather than doing a recursive call.
                    new_value.append(v)
                else:
                    new_value.append(self._normalize_search_value(v))
            return new_value

        # Otherwise, convert it into a Unicode string.
        return str(value)

    def __str__(self):
        """A human-readable representation of this SoupStrainer."""
        return self.string or f"{self.name}|{self.attrs}"
