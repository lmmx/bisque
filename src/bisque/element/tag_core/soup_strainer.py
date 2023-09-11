from __future__ import annotations

from re import Pattern
from typing import Callable

from pydantic import BaseModel, computed_field

from bisque.models import StrMixIn, StrTypes

__all__ = ["BaseSoupStrainer"]


class BaseSoupStrainer(BaseModel):
    """Encapsulates a number of ways of matching a markup element (tag or
    string).

    This is primarily used to underpin the find_* methods, but you can
    create one yourself and pass it in as `parse_only` to the
    `Bisque` constructor, to parse a subset of a large
    document.
    """

    name: str | bool | Pattern | list[str] | list | Callable | None = None
    attrs: dict = {}
    string: str | list[str] | bool | Pattern | None = None

    def __init__(
        self,
        name: str | bool | Pattern | list[str] | list | Callable | None = None,
        attrs: dict = {},
        string: str | list[str] | bool | Pattern | None = None,
        **kwargs,
    ):
        """Constructor.

        The SoupStrainer constructor takes the same arguments passed
        into the find_* methods. See the online documentation for
        detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param string: A filter for a NavigableString with specific text.
        :kwargs: A dictionary of filters on attribute values.
        """
        normal_name = self._normalize_search_value(name)
        if not isinstance(attrs, dict):
            # Treat a non-dict value for attrs as a search for the 'class' attribute.
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
        normal_attrs = {}
        for key, value in list(attrs.items()):
            normal_attrs[key] = self._normalize_search_value(value)
        normal_string = self._normalize_search_value(string)
        super().__init__(name=normal_name, attrs=normal_attrs, string=normal_string)

    @computed_field
    @property
    def text(self) -> str | None:
        """Allegedly deprecated but still used in tests."""
        return self.string

    def _normalize_search_value(self, value):
        # Leave it alone if it's a Unicode string, a callable, a
        # regular expression, a boolean, or None.
        if (
            isinstance(value, StrTypes)
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
                    and not isinstance(v, StrTypes)
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

    def search_tag(self, markup_name=None, markup_attrs={}):
        """Check whether a Tag with the given name and attributes would
        match this SoupStrainer.

        Used prospectively to decide whether to even bother creating a Tag
        object.

        :param markup_name: A tag name as found in some markup.
        :param markup_attrs: A dictionary of attributes as found in some markup.

        :return: True if the prospective tag would match this SoupStrainer;
            False otherwise.
        """
        found = None
        markup = None
        if isinstance(markup_name, self.TYPE_TABLE.Tag):
            markup = markup_name
            markup_attrs = markup

        if isinstance(self.name, str):
            # Optimization for a very common case where the user is
            # searching for a tag with one specific name, and we're
            # looking at a tag with a different name.
            if markup and not markup.prefix and self.name != markup.name:
                return False

        call_function_with_tag_data = isinstance(
            self.name,
            Callable,
        ) and not isinstance(markup_name, self.TYPE_TABLE.Tag)

        if (
            (not self.name)
            or call_function_with_tag_data
            or (markup and self._matches(markup, self.name))
            or (not markup and self._matches(markup_name, self.name))
        ):
            if call_function_with_tag_data:
                match = self.name(markup_name, markup_attrs)
            else:
                match = True
                markup_attr_map = None
                for attr, match_against in list(self.attrs.items()):
                    if not markup_attr_map:
                        if hasattr(markup_attrs, "get"):
                            markup_attr_map = markup_attrs
                        else:
                            markup_attr_map = {}
                            for k, v in markup_attrs:
                                markup_attr_map[k] = v
                    attr_value = markup_attr_map.get(attr)
                    if not self._matches(attr_value, match_against):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markup_name
        if found and self.string and not self._matches(found.string, self.string):
            found = None
        return found

    def search(self, markup):
        """Find all items in `markup` that match this SoupStrainer.

        Used by the core _find_all() method, which is ultimately
        called by all find_* methods.

        :param markup: A PageElement or a list of them.
        """
        # print('looking for %s in %s' % (self, markup))
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if hasattr(markup, "__iter__") and not isinstance(
            markup,
            (self.TYPE_TABLE.Tag, StrTypes),
        ):
            for element in markup:
                if isinstance(element, self.TYPE_TABLE.NavigableString) and self.search(
                    element,
                ):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, self.TYPE_TABLE.Tag):
            if not self.string or self.name or self.attrs:
                found = self.search_tag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, self.TYPE_TABLE.NavigableString) or isinstance(
            markup,
            StrTypes,
        ):
            if not self.name and not self.attrs and self._matches(markup, self.string):
                found = markup
        else:
            raise Exception("I don't know how to match against a %s" % markup.__class__)
        return found

    def _matches(self, markup, match_against, already_tried=None):
        # print(u"Matching %s against %s" % (markup, match_against))
        if isinstance(markup, list) or isinstance(markup, tuple):
            # This should only happen when searching a multi-valued attribute
            # like 'class'.
            for item in markup:
                if self._matches(item, match_against):
                    return True
            # We didn't match any particular value of the multivalue
            # attribute, but maybe we match the attribute value when
            # considered as a string.
            if self._matches(" ".join(markup), match_against):
                return True
            return False
        if match_against is True:
            # True matches any non-None value.
            return markup is not None
        if isinstance(match_against, Callable):
            return match_against(markup)
        # Custom callables take the tag as an argument, but all
        # other ways of matching match the tag name as a string.
        original_markup = markup
        if isinstance(markup, self.TYPE_TABLE.Tag):
            markup = markup.name
        # Ensure that `markup` is either a Unicode string, or None.
        markup = self._normalize_search_value(markup)
        if markup is None:
            # None matches None, False, an empty string, an empty list, and so on.
            return not match_against
        if hasattr(match_against, "__iter__") and not isinstance(
            match_against,
            StrTypes,
        ):
            # We're asked to match against an iterable of items.
            # The markup must be match at least one item in the
            # iterable. We'll try each one in turn.
            #
            # To avoid infinite recursion we need to keep track of
            # items we've already seen.
            if not already_tried:
                already_tried = set()
            for item in match_against:
                if item.__hash__:
                    key = item
                else:
                    key = id(item)
                if key in already_tried:
                    continue
                else:
                    already_tried.add(key)
                    if self._matches(original_markup, item, already_tried):
                        return True
            else:
                return False
        # Beyond this point we might need to run the test twice: once against
        # the tag's name and once against its prefixed name.
        match = False
        if not match and isinstance(match_against, StrTypes):
            # Exact string match
            match = markup == match_against
        if not match and hasattr(match_against, "search"):
            # Regexp match
            is_model = isinstance(markup, StrMixIn)
            return match_against.search(str(markup) if is_model else markup)
        if (
            not match
            and isinstance(original_markup, self.TYPE_TABLE.Tag)
            and original_markup.prefix
        ):
            # Try the whole thing again with the prefixed tag name.
            return self._matches(
                original_markup.prefix + ":" + original_markup.name,
                match_against,
            )
        return match
