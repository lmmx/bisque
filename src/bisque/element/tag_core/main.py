from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from ...models import StrMixIn, StrTypes
from ...typing.tabulation import BaseTypeTable
from .page_element import BasePageElement
from .soup_strainer import BaseSoupStrainer
from .string_types import (
    BaseCData,
    BaseComment,
    BaseDeclaration,
    BaseDoctype,
    BaseNavigableString,
    BasePreformattedString,
    BaseProcessingInstruction,
    BaseRubyParenthesisString,
    BaseRubyTextString,
    BaseScript,
    BaseStylesheet,
    BaseTemplateString,
    BaseXMLProcessingInstruction,
)
from .tag import BaseTag

__all__ = [
    # Section 0: central type registration
    "TYPE_TABLE",
    "TabulatedType",
    # Section 1: base element type
    "PageElement",
    # Section 2: string types
    "NavigableString",
    "PreformattedString",
    "CData",
    "ProcessingInstruction",
    "XMLProcessingInstruction",
    "Comment",
    "Declaration",
    "Doctype",
    "Stylesheet",
    "Script",
    "TemplateString",
    "RubyTextString",
    "RubyParenthesisString",
    # Section 3: base tag type
    "Tag",
    # Section 4: tree search helper types
    "SoupStrainer",
    "ResultSet",
]


class TYPE_TABLE(BaseTypeTable):
    # Section 1
    PageElement: ClassVar[type[PageElement]]  # Tabulated
    # Section 2
    NavigableString: ClassVar[type[NavigableString]]
    PreformattedString: ClassVar[type[PreformattedString]]
    CData: ClassVar[type[CData]]
    ProcessingInstruction: ClassVar[type[ProcessingInstruction]]
    XMLProcessingInstruction: ClassVar[type[XMLProcessingInstruction]]
    Comment: ClassVar[type[Comment]]
    Declaration: ClassVar[type[Declaration]]
    Doctype: ClassVar[type[Doctype]]
    Stylesheet: ClassVar[type[Stylesheet]]
    Script: ClassVar[type[Script]]
    TemplateString: ClassVar[type[TemplateString]]
    RubyTextString: ClassVar[type[RubyTextString]]
    RubyParenthesisString: ClassVar[type[RubyParenthesisString]]
    # Section 3
    Tag: ClassVar[type[Tag]]
    # Section 4
    SoupStrainer: ClassVar[type[SoupStrainer]]
    ResultSet: ClassVar[type[ResultSet]]


class TabulatedType:
    TYPE_TABLE: ClassVar[type[TYPE_TABLE]] = TYPE_TABLE


# Section 1: PageElement (1 class)


class PageElement(BasePageElement, TabulatedType):
    """Contains the navigational information for some part of the page:
    that is, its current location in the parse tree.

    NavigableString, Tag, etc. are all subclasses of PageElement.
    """


# Section 2: Text strings (13 classes)


class NavigableString(BaseNavigableString, PageElement, TabulatedType):
    """A Python Unicode string that is part of a parse tree.

    When Bisque parses the markup <b>penguin</b>, it will
    create a NavigableString for the string "penguin".
    """


class PreformattedString(BasePreformattedString, NavigableString, TabulatedType):
    """A NavigableString not subject to the normal formatting rules.

    This is an abstract class used for special kinds of strings such
    as comments (the Comment class) and CDATA blocks (the CData
    class).
    """


class CData(BaseCData, PreformattedString, TabulatedType):
    """A CDATA block."""


class ProcessingInstruction(
    BaseProcessingInstruction,
    PreformattedString,
    TabulatedType,
):
    """A SGML processing instruction."""


class XMLProcessingInstruction(
    BaseXMLProcessingInstruction,
    ProcessingInstruction,
    TabulatedType,
):
    """An XML processing instruction."""


class Comment(BaseComment, PreformattedString, TabulatedType):
    """An HTML or XML comment."""


class Declaration(BaseDeclaration, PreformattedString, TabulatedType):
    """An XML declaration."""


class Doctype(BaseDoctype, PreformattedString, TabulatedType):
    """A document type declaration."""


class Stylesheet(BaseStylesheet, NavigableString, TabulatedType):
    """A NavigableString representing an stylesheet (probably
    CSS).

    Used to distinguish embedded stylesheets from textual content.
    """


class Script(BaseScript, NavigableString, TabulatedType):
    """A NavigableString representing an executable script (probably
    Javascript).

    Used to distinguish executable code from textual content.
    """


class TemplateString(BaseTemplateString, NavigableString, TabulatedType):
    """A NavigableString representing a string found inside an HTML
    template embedded in a larger document.

    Used to distinguish such strings from the main body of the document.
    """


class RubyTextString(BaseRubyTextString, NavigableString, TabulatedType):
    """A NavigableString representing the contents of the <rt> HTML
    element.

    https://dev.w3.org/html5/spec-LC/text-level-semantics.html#the-rt-element

    Can be used to distinguish such strings from the strings they're
    annotating.
    """


class RubyParenthesisString(BaseRubyParenthesisString, NavigableString, TabulatedType):
    """A NavigableString representing the contents of the <rp> HTML
    element.

    https://dev.w3.org/html5/spec-LC/text-level-semantics.html#the-rp-element
    """


# Section 3: Tag (1 class)


class Tag(BaseTag, PageElement, TabulatedType):
    """Methods and attributes for Tag which are inseparable from the
    definitions of other classes in `bisque.element.tag_core.main`. Standalone methods
    are provided by inheritance from `bisque.element.tag_core.tag.BaseTag`.

    Represents an HTML or XML tag that is part of a parse tree, along
    with its attributes and contents.

    When Bisque parses the markup <b>penguin</b>, it will
    create a Tag object representing the <b> tag.
    """


# Section 4 (1 class)


class SoupStrainer(BaseSoupStrainer, TabulatedType):
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
        if isinstance(markup_name, Tag):
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
        ) and not isinstance(markup_name, Tag)

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
        if hasattr(markup, "__iter__") and not isinstance(markup, (Tag, StrTypes)):
            for element in markup:
                if isinstance(element, NavigableString) and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.string or self.name or self.attrs:
                found = self.search_tag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or isinstance(markup, StrTypes):
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
        if isinstance(markup, Tag):
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

        if not match and isinstance(original_markup, Tag) and original_markup.prefix:
            # Try the whole thing again with the prefixed tag name.
            return self._matches(
                original_markup.prefix + ":" + original_markup.name,
                match_against,
            )

        return match


class ResultSet(list, TabulatedType):
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


TYPE_TABLE.setup()
