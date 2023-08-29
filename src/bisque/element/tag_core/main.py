from __future__ import annotations

import warnings
from collections.abc import Callable

from bisque.formatter import Formatter

from ..encodings import DEFAULT_OUTPUT_ENCODING
from .page_element import PageElementBase
from .soup_strainer import SoupStrainerBase
from .tag import TagBase

__all__ = [
    # Section 1
    "PageElement",
    # Section 2
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
    # Section 3
    "Tag",
    # Section 4
    "SoupStrainer",
    "ResultSet",
]

# Section 1: PageElement (1 class)


class PageElement(PageElementBase):
    """Methods and attributes for PageElement which are inseparable from the
    definitions of other classes in `bisque.element.tag_core.main`. Standalone methods
    are provided by inheritance from `bisque.element.tag_core.page_element.PageElementBase`.

    Contains the navigational information for some part of the page:
    that is, its current location in the parse tree.

    NavigableString, Tag, etc. are all subclasses of PageElement.
    """

    def _last_descendant(self, is_initialized=True, accept_self=True):
        """Finds the last element beneath this object to be parsed.

        :param is_initialized: Has `setup` been called on this PageElement
            yet?
        :param accept_self: Is `self` an acceptable answer to the question?
        """
        if is_initialized and self.next_sibling is not None:
            last_child = self.next_sibling.previous_element
        else:
            last_child = self
            while isinstance(last_child, Tag) and last_child.contents:
                last_child = last_child.contents[-1]
        if not accept_self and last_child is self:
            last_child = None
        return last_child

    def insert(self, position, new_child):
        """Insert a new PageElement in the list of this PageElement's children.

        This works the same way as `list.insert`.

        :param position: The numeric position that should be occupied
           in `self.children` by the new PageElement.
        :param new_child: A PageElement.
        """
        if new_child is None:
            raise ValueError("Cannot insert None into a tag.")
        if new_child is self:
            raise ValueError("Cannot insert a tag into itself.")
        if isinstance(new_child, str) and not isinstance(new_child, NavigableString):
            new_child = NavigableString(new_child)

        from bisque import Bisque

        if isinstance(new_child, Bisque):
            # We don't want to end up with a situation where one Bisque
            # object contains another. Insert the children one at a time.
            for subchild in list(new_child.contents):
                self.insert(position, subchild)
                position += 1
            return
        position = min(position, len(self.contents))
        if hasattr(new_child, "parent") and new_child.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if new_child.parent is self:
                current_index = self.index(new_child)
                if current_index < position:
                    # We're moving this element further down the list
                    # of this object's children. That means that when
                    # we extract this element, our target index will
                    # jump down one.
                    position -= 1
            new_child.extract()

        new_child.parent = self
        previous_child = None
        if position == 0:
            new_child.previous_sibling = None
            new_child.previous_element = self
        else:
            previous_child = self.contents[position - 1]
            new_child.previous_sibling = previous_child
            new_child.previous_sibling.next_sibling = new_child
            new_child.previous_element = previous_child._last_descendant(False)
        if new_child.previous_element is not None:
            new_child.previous_element.next_element = new_child

        new_childs_last_element = new_child._last_descendant(False)

        if position >= len(self.contents):
            new_child.next_sibling = None

            parent = self
            parents_next_sibling = None
            while parents_next_sibling is None and parent is not None:
                parents_next_sibling = parent.next_sibling
                parent = parent.parent
                if parents_next_sibling is not None:
                    # We found the element that comes next in the document.
                    break
            if parents_next_sibling is not None:
                new_childs_last_element.next_element = parents_next_sibling
            else:
                # The last element of this tag is the last element in
                # the document.
                new_childs_last_element.next_element = None
        else:
            next_child = self.contents[position]
            new_child.next_sibling = next_child
            if new_child.next_sibling is not None:
                new_child.next_sibling.previous_sibling = new_child
            new_childs_last_element.next_element = next_child

        if new_childs_last_element.next_element is not None:
            new_childs_last_element.next_element.previous_element = (
                new_childs_last_element
            )
        self.contents.insert(position, new_child)

    def extend(self, tags):
        """Appends the given PageElements to this one's contents.

        :param tags: A list of PageElements. If a single Tag is
            provided instead, this PageElement's contents will be extended
            with that Tag's contents.
        """
        if isinstance(tags, Tag):
            tags = tags.contents
        if isinstance(tags, list):
            # Moving items around the tree may change their position in
            # the original list. Make a list that won't change.
            tags = list(tags)
        for tag in tags:
            self.append(tag)

    def insert_before(self, *args):
        """Makes the given element(s) the immediate predecessor of this one.

        All the elements will have the same parent, and the given elements
        will be immediately before this one.

        :param args: One or more PageElements.
        """
        parent = self.parent
        if parent is None:
            raise ValueError("Element has no parent, so 'before' has no meaning.")
        if any(x is self for x in args):
            raise ValueError("Can't insert an element before itself.")
        for predecessor in args:
            # Extract first so that the index won't be screwed up if they
            # are siblings.
            if isinstance(predecessor, PageElement):
                predecessor.extract()
            index = parent.index(self)
            parent.insert(index, predecessor)

    def insert_after(self, *args):
        """Makes the given element(s) the immediate successor of this one.

        The elements will have the same parent, and the given elements
        will be immediately after this one.

        :param args: One or more PageElements.
        """
        # Do all error checking before modifying the tree.
        parent = self.parent
        if parent is None:
            raise ValueError("Element has no parent, so 'after' has no meaning.")
        if any(x is self for x in args):
            raise ValueError("Can't insert an element after itself.")

        offset = 0
        for successor in args:
            # Extract first so that the index won't be screwed up if they
            # are siblings.
            if isinstance(successor, PageElement):
                successor.extract()
            index = parent.index(self)
            parent.insert(index + 1 + offset, successor)
            offset += 1

    def find_next(self, name=None, attrs={}, string=None, **kwargs):
        """Find the first PageElement that matches the given criteria and
        appears later in the document than this PageElement.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param string: A filter for a NavigableString with specific text.
        :kwargs: A dictionary of filters on attribute values.
        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        return self._find_one(self.find_all_next, name, attrs, string, **kwargs)

    def find_next_siblings(
        self,
        name=None,
        attrs={},
        string=None,
        limit=None,
        **kwargs,
    ) -> ResultSet:
        """Find all siblings of this PageElement that match the given criteria
        and appear later in the document.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param string: A filter for a NavigableString with specific text.
        :param limit: Stop looking after finding this many results.
        :kwargs: A dictionary of filters on attribute values.
        :return: A ResultSet of PageElements.
        :rtype: bisque.element.ResultSet
        """
        _stacklevel = kwargs.pop("_stacklevel", 2)
        return self._find_all(
            name,
            attrs,
            string,
            limit,
            self.next_siblings,
            _stacklevel=_stacklevel + 1,
            **kwargs,
        )

    def _find_all(self, name, attrs, string, limit, generator, **kwargs) -> ResultSet:
        "Iterates over a generator looking for things that match."
        _stacklevel = kwargs.pop("_stacklevel", 3)

        if string is None and "text" in kwargs:
            string = kwargs.pop("text")
            warnings.warn(
                "The 'text' argument to find()-type methods is deprecated. Use 'string' instead.",
                DeprecationWarning,
                stacklevel=_stacklevel,
            )

        if isinstance(name, SoupStrainer):
            strainer = name
        else:
            strainer = SoupStrainer(name, attrs, string, **kwargs)

        if string is None and not limit and not attrs and not kwargs:
            if name is True or name is None:
                # Optimization to find all tags.
                result = (element for element in generator if isinstance(element, Tag))
                return ResultSet(strainer, result)
            elif isinstance(name, str):
                # Optimization to find all tags with a given name.
                if name.count(":") == 1:
                    # This is a name with a prefix. If this is a namespace-aware document,
                    # we need to match the local name against tag.name. If not,
                    # we need to match the fully-qualified name against tag.name.
                    prefix, local_name = name.split(":", 1)
                else:
                    prefix = None
                    local_name = name
                result = (
                    element
                    for element in generator
                    if isinstance(element, Tag)
                    and (element.name == name)
                    or (
                        element.name == local_name
                        and (prefix is None or element.prefix == prefix)
                    )
                )
                return ResultSet(strainer, result)
        results = ResultSet(strainer)
        while True:
            try:
                i = next(generator)
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results


# Section 2: Text strings (13 classes)


class NavigableString(str, PageElement):
    """A Python Unicode string that is part of a parse tree.

    When Bisque parses the markup <b>penguin</b>, it will
    create a NavigableString for the string "penguin".
    """

    PREFIX = ""
    SUFFIX = ""

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, str):
            u = str.__new__(cls, value)
        else:
            u = str.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)
        u.setup()
        return u

    def __deepcopy__(self, memo, recursive=False):
        """A copy of a NavigableString has the same contents and class
        as the original, but it is not connected to the parse tree.

        :param recursive: This parameter is ignored; it's only defined
           so that NavigableString.__deepcopy__ implements the same
           signature as Tag.__deepcopy__.
        """
        return type(self)(self)

    def __copy__(self):
        """A copy of a NavigableString can only be a deep copy, because
        only one PageElement can occupy a given place in a parse tree.
        """
        return self.__deepcopy__({})

    def __getnewargs__(self):
        return (str(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == "string":
            return self
        else:
            raise AttributeError(
                "'{}' object has no attribute '{}'".format(
                    self.__class__.__name__,
                    attr,
                ),
            )

    def output_ready(self, formatter="minimal"):
        """Run the string through the provided formatter.

        :param formatter: A Formatter object, or a string naming one of the standard formatters.
        """
        output = self.format_string(self, formatter)
        return self.PREFIX + output + self.SUFFIX

    @property
    def name(self):
        """Since a NavigableString is not a Tag, it has no .name.

        This property is implemented so that code like this doesn't crash
        when run on a mixture of Tag and NavigableString objects:
            [x.name for x in tag.children]
        """
        return None

    @name.setter
    def name(self, name):
        """Prevent NavigableString.name from ever being set."""
        raise AttributeError("A NavigableString cannot be given a name.")

    def _all_strings(self, strip=False, types=PageElement.default):
        """Yield all strings of certain classes, possibly stripping them.

        This makes it easy for NavigableString to implement methods
        like get_text() as conveniences, creating a consistent
        text-extraction API across all PageElements.

        :param strip: If True, all strings will be stripped before being
            yielded.

        :param types: A tuple of NavigableString subclasses. If this
            NavigableString isn't one of those subclasses, the
            sequence will be empty. By default, the subclasses
            considered are NavigableString and CData objects. That
            means no comments, processing instructions, etc.

        :yield: A sequence that either contains this string, or is empty.

        """
        if types is self.default:
            # This is kept in Tag because it's full of subclasses of
            # this class, which aren't defined until later in the file.
            types = Tag.DEFAULT_INTERESTING_STRING_TYPES

        # Do nothing if the caller is looking for specific types of
        # string, and we're of a different type.
        #
        # We check specific types instead of using isinstance(self,
        # types) because all of these classes subclass
        # NavigableString. Anyone who's using this feature probably
        # wants generic NavigableStrings but not other stuff.
        my_type = type(self)
        if types is not None:
            if isinstance(types, type):
                # Looking for a single type.
                if my_type is not types:
                    return
            elif my_type not in types:
                # Looking for one of a list of types.
                return

        value = self
        if strip:
            value = value.strip()
        if len(value) > 0:
            yield value

    strings = property(_all_strings)


class PreformattedString(NavigableString):
    """A NavigableString not subject to the normal formatting rules.

    This is an abstract class used for special kinds of strings such
    as comments (the Comment class) and CDATA blocks (the CData
    class).
    """

    PREFIX = ""
    SUFFIX = ""

    def output_ready(self, formatter=None):
        """Make this string ready for output by adding any subclass-specific
            prefix or suffix.

        :param formatter: A Formatter object, or a string naming one
            of the standard formatters. The string will be passed into the
            Formatter, but only to trigger any side effects: the return
            value is ignored.

        :return: The string, with any subclass-specific prefix and
           suffix added on.
        """
        if formatter is not None:
            # this used to assign to an unused var named "ignore"
            self.format_string(self, formatter)
        return self.PREFIX + self + self.SUFFIX


class CData(PreformattedString):
    """A CDATA block."""

    PREFIX = "<![CDATA["
    SUFFIX = "]]>"


class ProcessingInstruction(PreformattedString):
    """A SGML processing instruction."""

    PREFIX = "<?"
    SUFFIX = ">"


class XMLProcessingInstruction(ProcessingInstruction):
    """An XML processing instruction."""

    PREFIX = "<?"
    SUFFIX = "?>"


class Comment(PreformattedString):
    """An HTML or XML comment."""

    PREFIX = "<!--"
    SUFFIX = "-->"


class Declaration(PreformattedString):
    """An XML declaration."""

    PREFIX = "<?"
    SUFFIX = "?>"


class Doctype(PreformattedString):
    """A document type declaration."""

    @classmethod
    def for_name_and_ids(cls, name, pub_id, system_id):
        """Generate an appropriate document type declaration for a given
        public ID and system ID.

        :param name: The name of the document's root element, e.g. 'html'.
        :param pub_id: The Formal Public Identifier for this document type,
            e.g. '-//W3C//DTD XHTML 1.1//EN'
        :param system_id: The system identifier for this document type,
            e.g. 'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'

        :return: A Doctype.
        """
        value = name or ""
        if pub_id is not None:
            value += ' PUBLIC "%s"' % pub_id
            if system_id is not None:
                value += ' "%s"' % system_id
        elif system_id is not None:
            value += ' SYSTEM "%s"' % system_id

        return Doctype(value)

    PREFIX = "<!DOCTYPE "
    SUFFIX = ">\n"


class Stylesheet(NavigableString):
    """A NavigableString representing an stylesheet (probably
    CSS).

    Used to distinguish embedded stylesheets from textual content.
    """


class Script(NavigableString):
    """A NavigableString representing an executable script (probably
    Javascript).

    Used to distinguish executable code from textual content.
    """


class TemplateString(NavigableString):
    """A NavigableString representing a string found inside an HTML
    template embedded in a larger document.

    Used to distinguish such strings from the main body of the document.
    """


class RubyTextString(NavigableString):
    """A NavigableString representing the contents of the <rt> HTML
    element.

    https://dev.w3.org/html5/spec-LC/text-level-semantics.html#the-rt-element

    Can be used to distinguish such strings from the strings they're
    annotating.
    """


class RubyParenthesisString(NavigableString):
    """A NavigableString representing the contents of the <rp> HTML
    element.

    https://dev.w3.org/html5/spec-LC/text-level-semantics.html#the-rp-element
    """


# Section 3: Tag (1 class)


class Tag(TagBase, PageElement):
    """Methods and attributes for Tag which are inseparable from the
    definitions of other classes in `bisque.element.tag_core.main`. Standalone methods
    are provided by inheritance from `bisque.element.tag_core.tag.TagBase`.

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

    def _all_strings(self, strip=False, types=PageElement.default):
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
        if types is self.default:
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


class SoupStrainer(SoupStrainerBase):
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


class ResultSet(list):
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
