from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from bisque.formatter import Formatter

from ...typing.tabulation import BaseTypeTable
from ..encodings import DEFAULT_OUTPUT_ENCODING
from ..sentinels import DEFAULT_TYPES_SENTINEL
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

    def __deepcopy__(self, memo, recursive=True):
        """A deepcopy of a Tag is a new Tag, unconnected to the parse tree.
        Its contents are a copy of the old Tag's contents.
        """
        clone = self._clone()

        if recursive:
            # Clone this tag's descendants recursively, but without
            # making any recursive function calls.
            tag_stack = [clone]
            for event, element in self._event_stream(self.descendants):
                if event is Tag.END_ELEMENT_EVENT:
                    # Stop appending incoming Tags to the Tag that was
                    # just closed.
                    tag_stack.pop()
                else:
                    descendant_clone = element.__deepcopy__(memo, recursive=False)
                    # Add to its parent's .contents
                    tag_stack[-1].append(descendant_clone)

                    if event is Tag.START_ELEMENT_EVENT:
                        # Add the Tag itself to the stack so that its
                        # children will be .appended to it.
                        tag_stack.append(descendant_clone)
        return clone

    @property
    def string(self):
        """Convenience property to get the single string within this
        PageElement.

        TODO It might make sense to have NavigableString.string return
        itself.

        :return: If this element has a single string child, return
         value is that string. If this element has one child tag,
         return value is the 'string' attribute of the child tag,
         recursively. If this element is itself a string, has no
         children, or has more than one child, return value is None.
        """
        if len(self.contents) != 1:
            return None
        child = self.contents[0]
        if isinstance(child, NavigableString):
            return child
        return child.string

    @string.setter
    def string(self, string):
        """Replace this PageElement's contents with `string`."""
        self.clear()
        self.append(string.__class__(string))

    DEFAULT_INTERESTING_STRING_TYPES = (NavigableString, CData)

    def _all_strings(self, strip=False, types=DEFAULT_TYPES_SENTINEL):
        """Yield all strings of certain classes, possibly stripping them.

        :param strip: If True, all strings will be stripped before being
            yielded.

        :param types: A tuple of NavigableString subclasses. Any strings of
            a subclass not found in this list will be ignored. By
            default, the subclasses considered are the ones found in
            self.interesting_string_types. If that's not specified,
            only NavigableString and CData objects will be
            considered. That means no comments, processing
            instructions, etc.

        :yield: A sequence of strings.

        """
        if types is DEFAULT_TYPES_SENTINEL:
            types = self.interesting_string_types

        for descendant in self.descendants:
            if types is None and not isinstance(descendant, NavigableString):
                continue
            descendant_type = type(descendant)
            if isinstance(types, type):
                if descendant_type is not types:
                    # We're not interested in strings of this type.
                    continue
            elif types is not None and descendant_type not in types:
                # We're not interested in strings of this type.
                continue
            if strip:
                descendant = descendant.strip()
                if len(descendant) == 0:
                    continue
            yield descendant

    strings = property(_all_strings)

    def clear(self, decompose=False):
        """Wipe out all children of this PageElement by calling extract()
           on them.

        :param decompose: If this is True, decompose() (a more
            destructive method) will be called instead of extract().
        """
        if decompose:
            for element in self.contents[:]:
                if isinstance(element, Tag):
                    element.decompose()
                else:
                    element.extract()
        else:
            for element in self.contents[:]:
                element.extract()

    def smooth(self):
        """Smooth out this element's children by consolidating consecutive
        strings.

        This makes pretty-printed output look more natural following a
        lot of operations that modified the tree.
        """
        # Mark the first position of every pair of children that need
        # to be consolidated.  Do this rather than making a copy of
        # self.contents, since in most cases very few strings will be
        # affected.
        marked = []
        for i, a in enumerate(self.contents):
            if isinstance(a, Tag):
                # Recursively smooth children.
                a.smooth()
            if i == len(self.contents) - 1:
                # This is the last item in .contents, and it's not a
                # tag. There's no chance it needs any work.
                continue
            b = self.contents[i + 1]
            if (
                isinstance(a, NavigableString)
                and isinstance(b, NavigableString)
                and not isinstance(a, PreformattedString)
                and not isinstance(b, PreformattedString)
            ):
                marked.append(i)

        # Go over the marked positions in reverse order, so that
        # removing items from .contents won't affect the remaining
        # positions.
        for i in reversed(marked):
            a = self.contents[i]
            b = self.contents[i + 1]
            b.extract()
            n = NavigableString(a + b)
            a.replace_with(n)

    def decode(
        self,
        indent_level=None,
        eventual_encoding=DEFAULT_OUTPUT_ENCODING,
        formatter="minimal",
        iterator=None,
    ):
        pieces = []
        # First off, turn a non-Formatter `formatter` into a Formatter
        # object. This will stop the lookup from happening over and
        # over again.
        if not isinstance(formatter, Formatter):
            formatter = self.formatter_for_name(formatter)

        if indent_level is True:
            indent_level = 0

        # The currently active tag that put us into string literal
        # mode. Until this element is closed, children will be treated
        # as string literals and not pretty-printed. String literal
        # mode is turned on immediately after this tag begins, and
        # turned off immediately before it's closed. This means there
        # will be whitespace before and after the tag itself.
        string_literal_tag = None

        for event, element in self._event_stream(iterator):
            if event in (Tag.START_ELEMENT_EVENT, Tag.EMPTY_ELEMENT_EVENT):
                piece = element._format_tag(eventual_encoding, formatter, opening=True)
            elif event is Tag.END_ELEMENT_EVENT:
                piece = element._format_tag(eventual_encoding, formatter, opening=False)
                if indent_level is not None:
                    indent_level -= 1
            else:
                piece = element.output_ready(formatter)

            # Now we need to apply the 'prettiness' -- extra
            # whitespace before and/or after this tag. This can get
            # complicated because certain tags, like <pre> and
            # <script>, can't be prettified, since adding whitespace would
            # change the meaning of the content.

            # The default behavior is to add whitespace before and
            # after an element when string literal mode is off, and to
            # leave things as they are when string literal mode is on.
            if string_literal_tag:
                indent_before = indent_after = False
            else:
                indent_before = indent_after = True

            # The only time the behavior is more complex than that is
            # when we encounter an opening or closing tag that might
            # put us into or out of string literal mode.
            if (
                event is Tag.START_ELEMENT_EVENT
                and not string_literal_tag
                and not element._should_pretty_print()
            ):
                # We are about to enter string literal mode. Add
                # whitespace before this tag, but not after. We
                # will stay in string literal mode until this tag
                # is closed.
                indent_before = True
                indent_after = False
                string_literal_tag = element
            elif event is Tag.END_ELEMENT_EVENT and element is string_literal_tag:
                # We are about to exit string literal mode by closing
                # the tag that sent us into that mode. Add whitespace
                # after this tag, but not before.
                indent_before = False
                indent_after = True
                string_literal_tag = None

            # Now we know whether to add whitespace before and/or
            # after this element.
            if indent_level is not None:
                if indent_before or indent_after:
                    if isinstance(element, NavigableString):
                        piece = piece.strip()
                    if piece:
                        piece = self._indent_string(
                            piece,
                            indent_level,
                            formatter,
                            indent_before,
                            indent_after,
                        )
                if event == Tag.START_ELEMENT_EVENT:
                    indent_level += 1
            pieces.append(piece)
        return "".join(pieces)

    def _event_stream(self, iterator=None):
        """Yield a sequence of events that can be used to reconstruct the DOM
        for this element.

        This lets us recreate the nested structure of this element
        (e.g. when formatting it as a string) without using recursive
        method calls.

        This is similar in concept to the SAX API, but it's a simpler
        interface designed for internal use. The events are different
        from SAX and the arguments associated with the events are Tags
        and other Bisque objects.

        :param iterator: An alternate iterator to use when traversing
         the tree.
        """
        tag_stack = []

        iterator = iterator or self.self_and_descendants

        for c in iterator:
            # If the parent of the element we're about to yield is not
            # the tag currently on the stack, it means that the tag on
            # the stack closed before this element appeared.
            while tag_stack and c.parent != tag_stack[-1]:
                now_closed_tag = tag_stack.pop()
                yield Tag.END_ELEMENT_EVENT, now_closed_tag

            if isinstance(c, Tag):
                if c.is_empty_element:
                    yield Tag.EMPTY_ELEMENT_EVENT, c
                else:
                    yield Tag.START_ELEMENT_EVENT, c
                    tag_stack.append(c)
                    continue
            else:
                yield Tag.STRING_ELEMENT_EVENT, c

        while tag_stack:
            now_closed_tag = tag_stack.pop()
            yield Tag.END_ELEMENT_EVENT, now_closed_tag

    def find_all(
        self,
        name=None,
        attrs={},
        recursive=True,
        string=None,
        limit=None,
        **kwargs,
    ) -> ResultSet:
        """Look in the children of this PageElement and find all
        PageElements that match the given criteria.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param recursive: If this is True, find_all() will perform a
            recursive search of this PageElement's children. Otherwise,
            only the direct children will be considered.
        :param limit: Stop looking after finding this many results.
        :kwargs: A dictionary of filters on attribute values.
        :return: A ResultSet of PageElements.
        :rtype: bisque.element.ResultSet
        """
        generator = self.descendants
        if not recursive:
            generator = self.children
        _stacklevel = kwargs.pop("_stacklevel", 2)
        return self._find_all(
            name,
            attrs,
            string,
            limit,
            generator,
            _stacklevel=_stacklevel + 1,
            **kwargs,
        )


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
        if hasattr(markup, "__iter__") and not isinstance(markup, (Tag, str)):
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
        elif isinstance(markup, NavigableString) or isinstance(markup, str):
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

        if hasattr(match_against, "__iter__") and not isinstance(match_against, str):
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

        if not match and isinstance(match_against, str):
            # Exact string match
            match = markup == match_against

        if not match and hasattr(match_against, "search"):
            # Regexp match
            return match_against.search(markup)

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
