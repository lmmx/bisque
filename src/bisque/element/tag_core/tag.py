from __future__ import annotations

import warnings
from typing import Any, ClassVar, Iterator

from pydantic import Field

from bisque.css import CSS
from bisque.formatter import Formatter
from bisque.models import Element, Entity

# from ...models import Element, Entity
from ..attributes import AttributeValueWithCharsetSubstitution
from ..encodings import DEFAULT_OUTPUT_ENCODING
from ..sentinels import DEFAULT_TYPES_SENTINEL, ElementEvent

__all__ = ["BaseTag"]

AnyElement = Any


class BaseTag(Element):
    """Standalone methods and attributes for Tag.

    Represents an HTML or XML tag that is part of a parse tree, along
    with its attributes and contents.

    When Bisque parses the markup <b>penguin</b>, it will
    create a Tag object representing the <b> tag.
    """

    # validated
    name: str
    namespace: str | None = None
    prefix: str | None = None
    attrs: dict = {}
    parent: Element | None = None  # TODO annotate as element (can't use Any)
    previous: Element | None = None  # TODO annotate as element (can't use Any)
    known_xml: bool | None = False
    sourceline: int | None = None
    sourcepos: int | None = None
    can_be_empty_element: bool = False
    cdata_list_attributes: list[str] | dict | None = []
    preserve_whitespace_tags: list[str] = []
    interesting_string_types: type | tuple[type, ...]  # default set in init
    namespaces: dict = {}
    # computed
    parser_class: type | None = None
    # invariant
    hidden: bool | int | None = None
    contents: list = []
    decomposed: bool = Field(False, repr=False)
    parent: Element | None = Field(None, repr=False)
    previous_element: Element | None = Field(None, repr=False)
    next_element: Element | None = Field(None, repr=False)
    previous_sibling: Element | None = Field(None, repr=False)
    next_sibling: Element | None = Field(None, repr=False)
    # class variables
    store_on_base: ClassVar[list[str]] = []

    def __init__(
        self,
        parser=None,
        builder=None,
        name=None,
        namespace=None,
        prefix=None,
        attrs=None,
        parent=None,
        previous=None,
        is_xml=None,
        sourceline=None,
        sourcepos=None,
        can_be_empty_element=False,
        cdata_list_attributes=None,
        preserve_whitespace_tags=None,
        interesting_string_types=None,
        namespaces=None,
        **kwargs,
    ):
        """Basic constructor.

        :param parser: A Bisque object.
        :param builder: A TreeBuilder.
        :param name: The name of the tag.
        :param namespace: The URI of this Tag's XML namespace, if any.
        :param prefix: The prefix for this Tag's XML namespace, if any.
        :param attrs: A dictionary of this Tag's attribute values.
        :param parent: The PageElement to use as this Tag's parent.
        :param previous: The PageElement that was parsed immediately before
            this tag.
        :param is_xml: If True, this is an XML tag. Otherwise, this is an
            HTML tag.
        :param sourceline: The line number where this tag was found in its
            source document.
        :param sourcepos: The character position within `sourceline` where this
            tag was found.
        :param can_be_empty_element: If True, this tag should be
            represented as <tag/>. If False, this tag should be represented
            as <tag></tag>.
        :param cdata_list_attributes: A list of attributes whose values should
            be treated as CDATA if they ever show up on this tag.
        :param preserve_whitespace_tags: A list of tag names whose contents
            should have their whitespace preserved.
        :param interesting_string_types: This is a NavigableString
            subclass or a tuple of them. When iterating over this
            Tag's strings in methods like Tag.strings or Tag.get_text,
            these are the types of strings that are interesting enough
            to be considered. The default is to consider
            NavigableString and CData the only interesting string
            subtypes.
        :param namespaces: A dictionary mapping currently active
            namespace prefixes to URIs. This can be used later to
            construct CSS selectors.
        """
        if cdata_list_attributes is None:
            cdata_list_attributes = []
        if preserve_whitespace_tags is None:
            preserve_whitespace_tags = []
        if interesting_string_types is None:
            interesting_string_types = (
                self.TYPE_TABLE.NavigableString,
                self.TYPE_TABLE.CData,
            )
        # This seems fragile but can no longer support this logic without a sentinel
        if (not builder or builder.store_line_numbers) and (
            sourceline is not None or sourcepos is not None
        ):
            kwargs.update(dict(sourceline=sourceline, sourcepos=sourcepos))
        if name is None:
            raise ValueError("No value provided for new tag's name.")
        namespaces = namespaces or {}
        if attrs is None:
            attrs = {}
        elif attrs:
            if builder is not None and builder.cdata_list_attributes:
                attrs = builder._replace_cdata_list_attribute_values(name, attrs)
            else:
                attrs = dict(attrs)
        else:
            attrs = dict(attrs)
        # In the absence of a TreeBuilder, use whatever values were passed in here.
        # They're probably None, unless this is a copy of some other tag.
        if builder is not None:
            # Ask the TreeBuilder whether this tag might be an empty-element tag.
            can_be_empty_element = builder.can_be_empty_element(name)
            # Keep track of the list of attributes of this tag that might need to
            # be treated as a list.
            #
            # For performance reasons, we store the whole data structure rather than
            # asking the question of every tag. Asking would require building a new
            # data structure every time, and (unlike can_be_empty_element), we almost
            # never need to check this.
            cdata_list_attributes = builder.cdata_list_attributes
            # Keep track of the names that might cause this tag to be treated as a
            # whitespace-preserved tag.
            preserve_whitespace_tags = builder.preserve_whitespace_tags
            if name in builder.string_containers:
                # This sort of tag uses a special string container subclass for most of
                # its strings. When we ask the (...rest of this comment is missing?)
                interesting_string_types = builder.string_containers[name]
        # We don't store the parser object so extracted chunks get garbage-collected.
        parser_class = None if parser is None else parser.__class__
        # If possible, determine ahead of time whether this tag is an XML tag.
        known_xml = is_xml if builder is None else builder.is_xml
        # Otherwise subclass fields that are also init args to this class aren't set
        # i.e. prevent them being 'consumed' here by putting them [back] into kwargs
        kwargs.update({kw: v for kw, v in locals().items() if kw in self.store_on_base})
        super().__init__(
            parser_class=parser_class,
            name=name,
            namespace=namespace,
            prefix=prefix,
            attrs=attrs,
            parent=parent,
            previous=previous,
            known_xml=known_xml,
            # sourceline=sourceline,
            # sourcepos=sourcepos,
            can_be_empty_element=can_be_empty_element or False,
            cdata_list_attributes=cdata_list_attributes,
            preserve_whitespace_tags=preserve_whitespace_tags,
            interesting_string_types=interesting_string_types,
            namespaces=namespaces,
            **kwargs,
        )
        self.setup(parent, previous)
        if builder is not None:
            # Set up any substitutions for this tag, such as the charset in a META tag.
            builder.set_up_substitutions(self)

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
                if event is ElementEvent.END:
                    # Stop appending incoming Tags to the Tag that was
                    # just closed.
                    tag_stack.pop()
                else:
                    descendant_clone = element.__deepcopy__(memo, recursive=False)
                    # Add to its parent's .contents
                    tag_stack[-1].append(descendant_clone)

                    if event is ElementEvent.START:
                        # Add the Tag itself to the stack so that its
                        # children will be .appended to it.
                        tag_stack.append(descendant_clone)
        return clone

    def __copy__(self):
        """A copy of a Tag must always be a deep copy, because a Tag's
        children can only have one parent at a time.
        """
        return self.__deepcopy__({})

    def _clone(self):
        """Create a new Tag just like this one, but with no
        contents and unattached to any parse tree.

        This is the first step in the deepcopy process.
        """
        clone = type(self)(
            None,
            None,
            self.name,
            self.namespace,
            self.prefix,
            self.attrs,
            is_xml=self._is_xml,
            sourceline=self.sourceline,
            sourcepos=self.sourcepos,
            can_be_empty_element=self.can_be_empty_element,
            cdata_list_attributes=self.cdata_list_attributes,
            preserve_whitespace_tags=self.preserve_whitespace_tags,
            interesting_string_types=self.interesting_string_types,
        )
        for attr in ("can_be_empty_element", "hidden"):
            setattr(clone, attr, getattr(self, attr))
        return clone

    @property
    def is_empty_element(self):
        """Is this tag an empty-element tag? (aka a self-closing tag)

        A tag that has contents is never an empty-element tag.

        A tag that has no contents may or may not be an empty-element
        tag. It depends on the builder used to create the tag. If the
        builder has a designated list of empty-element tags, then only
        a tag whose name shows up in that list is considered an
        empty-element tag.

        If the builder has no designated list of empty-element tags,
        then any tag with no contents is an empty-element tag.
        """
        return len(self.contents) == 0 and self.can_be_empty_element

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
        if isinstance(child, self.TYPE_TABLE.NavigableString):
            return child
        return child.string

    @string.setter
    def string(self, string):
        """Replace this PageElement's contents with `string`."""
        self.clear()
        if isinstance(string, str):
            self.append(string.__class__(string))
        else:
            self.append(string.__class__(value=string.value))

    def _all_strings(self, strip=False, types=DEFAULT_TYPES_SENTINEL) -> Iterator[str]:
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
            if types is None and not isinstance(
                descendant,
                self.TYPE_TABLE.NavigableString,
            ):
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
                is_model = issubclass(descendant_type, Entity)
                clone = descendant.model_copy() if is_model else descendant.copy()
                clone.value = descendant.value.strip()
                if len(clone) == 0:
                    continue
                returnable = clone
            else:
                returnable = descendant
            yield returnable

    strings = property(_all_strings)

    def decompose(self):
        """Recursively destroys this PageElement and its children.

        This element will be removed from the tree and wiped out; so
        will everything beneath it.

        The behavior of a decomposed PageElement is undefined and you
        should never use one for anything, but if you need to _check_
        whether an element has been decomposed, you can use the
        `has_decomposed` property.
        """
        self.extract()
        i = self
        while i is not None:
            n = i.next_element
            # Do this both before and after because of Pydantic field references
            i.contents = []
            i.decomposed = True
            i.clear()
            # Only needs repeating for Pydantic models (possible error in parent ref?)
            if isinstance(i, Entity):
                i.contents = []
                i.decomposed = True
            i = n

    def clear(self, decompose=False):
        """Wipe out all children of this PageElement by calling extract()
           on them.

        :param decompose: If this is True, decompose() (a more
            destructive method) will be called instead of extract().
        """
        if decompose:
            for element in self.contents[:]:
                if isinstance(element, self.TYPE_TABLE.Tag):
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
            if isinstance(a, self.TYPE_TABLE.Tag):
                # Recursively smooth children.
                a.smooth()
            if i == len(self.contents) - 1:
                # This is the last item in .contents, and it's not a
                # tag. There's no chance it needs any work.
                continue
            b = self.contents[i + 1]
            if (
                isinstance(a, self.TYPE_TABLE.NavigableString)
                and isinstance(b, self.TYPE_TABLE.NavigableString)
                and not isinstance(a, self.TYPE_TABLE.PreformattedString)
                and not isinstance(b, self.TYPE_TABLE.PreformattedString)
            ):
                marked.append(i)

        # Go over the marked positions in reverse order, so that
        # removing items from .contents won't affect the remaining
        # positions.
        for i in reversed(marked):
            a = self.contents[i]
            b = self.contents[i + 1]
            b.extract()
            n = self.TYPE_TABLE.NavigableString(a + b)
            a.replace_with(n)

    def index(self, element):
        """Find the index of a child by identity, not value.

        Avoids issues with tag.contents.index(element) getting the
        index of equal elements.

        :param element: Look for this PageElement in `self.contents`.
        """
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self.attrs.get(key, default)

    def get_attribute_list(self, key, default=None):
        """The same as get(), but always returns a list.

        :param key: The attribute to look for.
        :param default: Use this value if the attribute is not present
            on this PageElement.
        :return: A list of values, probably containing only a single
            value.
        """
        value = self.get(key, default)
        if not isinstance(value, list):
            value = [value]
        return value

    def has_attr(self, key):
        """Does this PageElement have an attribute with the given name?"""
        return key in self.attrs

    def __hash__(self):
        return str(self).__hash__()

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the Tag,
        and throws an exception if it's not there."""
        return self.attrs[key]

    def __iter__(self):
        "Iterating over a Tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a Tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __bool__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self.attrs[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        self.attrs.pop(key, None)

    def __call__(self, *args, **kwargs):
        """Calling a Tag like a function is the same as calling its
        find_all() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return self.find_all(*args, **kwargs)

    def __getattr__(self, tag):
        """Calling tag.subtag is the same as calling tag.find(name="subtag")"""
        # print("Getattr %s.%s" % (self.__class__, tag))
        # We special case contents to avoid recursion.
        if not tag.startswith("__") and tag != "contents":
            return self.find(tag)
        # raise AttributeError(
        #     f"'{self.__class__}' object has no attribute '{tag}'",
        # )

    def __eq__(self, other):
        """Returns true iff this Tag has the same name, the same attributes,
        and the same contents (recursively) as `other`."""
        if self is other:
            return True
        if (
            not hasattr(other, "name")
            or not hasattr(other, "attrs")
            or not hasattr(other, "contents")
            or self.name != other.name
            or self.attrs != other.attrs
            or len(self) != len(other)
        ):
            return False
        for i, my_child in enumerate(self.contents):
            if my_child != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this Tag is not identical to `other`,
        as defined in __eq__."""
        return not self == other

    def __unicode__(self):
        """Renders this PageElement as a Unicode string."""
        return self.decode()

    __str__ = __repr__ = __unicode__

    def encode(
        self,
        encoding=DEFAULT_OUTPUT_ENCODING,
        indent_level=None,
        formatter="minimal",
        errors="xmlcharrefreplace",
    ):
        """Render a bytestring representation of this PageElement and its
        contents.

        :param encoding: The destination encoding.
        :param indent_level: Each line of the rendering will be
           indented this many levels. (The formatter decides what a
           'level' means in terms of spaces or other characters
           output.) Used internally in recursive calls while
           pretty-printing.
        :param formatter: A Formatter object, or a string naming one of
            the standard formatters.
        :param errors: An error handling strategy such as
            'xmlcharrefreplace'. This value is passed along into
            encode() and its value should be one of the constants
            defined by Python.
        :return: A bytestring.

        """
        # Turn the data structure into Unicode, then encode the
        # Unicode.
        u = self.decode(indent_level, encoding, formatter)
        return u.encode(encoding, errors)

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
            if event in (
                ElementEvent.START,
                ElementEvent.EMPTY,
            ):
                piece = element._format_tag(eventual_encoding, formatter, opening=True)
            elif event is ElementEvent.END:
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
                event is ElementEvent.START
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
            elif event is ElementEvent.END and element is string_literal_tag:
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
                    if isinstance(element, self.TYPE_TABLE.NavigableString):
                        piece = piece.strip()
                    if piece:
                        piece = self._indent_string(
                            piece,
                            indent_level,
                            formatter,
                            indent_before,
                            indent_after,
                        )
                if event == ElementEvent.START:
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
                yield ElementEvent.END, now_closed_tag

            if isinstance(c, self.TYPE_TABLE.Tag):
                if c.is_empty_element:
                    yield ElementEvent.EMPTY, c
                else:
                    yield ElementEvent.START, c
                    tag_stack.append(c)
                    continue
            else:
                yield ElementEvent.STRING, c

        while tag_stack:
            now_closed_tag = tag_stack.pop()
            yield ElementEvent.END, now_closed_tag

    def _indent_string(self, s, indent_level, formatter, indent_before, indent_after):
        """Add indentation whitespace before and/or after a string.

        :param s: The string to amend with whitespace.
        :param indent_level: The indentation level; affects how much
           whitespace goes before the string.
        :param indent_before: Whether or not to add whitespace
           before the string.
        :param indent_after: Whether or not to add whitespace
           (a newline) after the string.
        """
        space_before = ""
        if indent_before and indent_level:
            space_before = formatter.indent * indent_level

        space_after = ""
        if indent_after:
            space_after = "\n"

        return space_before + s + space_after

    def _format_tag(self, eventual_encoding, formatter, opening):
        if self.hidden:
            # A hidden tag is invisible, although its contents
            # are visible.
            return ""

        # A tag starts with the < character (see below).

        # Then the / character, if this is a closing tag.
        closing_slash = ""
        if not opening:
            closing_slash = "/"

        # Then an optional namespace prefix.
        prefix = ""
        if self.prefix:
            prefix = self.prefix + ":"

        # Then a list of attribute values, if this is an opening tag.
        attribute_string = ""
        if opening:
            attributes = formatter.attributes(self)
            attrs = []
            for key, val in attributes:
                if val is None:
                    decoded = key
                else:
                    if isinstance(val, list) or isinstance(val, tuple):
                        val = " ".join(val)
                    elif (
                        isinstance(val, AttributeValueWithCharsetSubstitution)
                        and eventual_encoding is not None
                    ):
                        val = val.encode(eventual_encoding)
                    elif not isinstance(val, str):
                        val = str(val)

                    text = formatter.attribute_value(val)
                    decoded = str(key) + "=" + formatter.quoted_attribute_value(text)
                attrs.append(decoded)
            if attrs:
                attribute_string = " " + " ".join(attrs)

        # Then an optional closing slash (for a void element in an
        # XML document).
        void_element_closing_slash = ""
        if self.is_empty_element:
            void_element_closing_slash = formatter.void_element_close_prefix or ""

        # Put it all together.
        return (
            "<"
            + closing_slash
            + prefix
            + self.name
            + attribute_string
            + void_element_closing_slash
            + ">"
        )

    def _should_pretty_print(self, indent_level=1):
        """Should this tag be pretty-printed?

        Most of them should, but some (such as <pre> in HTML
        documents) should not.
        """
        return indent_level is not None and (
            not self.preserve_whitespace_tags
            or self.name not in self.preserve_whitespace_tags
        )

    def prettify(self, encoding=None, formatter="minimal"):
        """Pretty-print this PageElement as a string.

        :param encoding: The eventual encoding of the string. If this is None,
            a Unicode string will be returned.
        :param formatter: A Formatter object, or a string naming one of
            the standard formatters.
        :return: A Unicode string (if encoding==None) or a bytestring
            (otherwise).
        """
        if encoding is None:
            return self.decode(True, formatter=formatter)
        else:
            return self.encode(encoding, True, formatter=formatter)

    def decode_contents(
        self,
        indent_level=None,
        eventual_encoding=DEFAULT_OUTPUT_ENCODING,
        formatter="minimal",
    ):
        """Renders the contents of this tag as a Unicode string.

        :param indent_level: Each line of the rendering will be
           indented this many levels. (The formatter decides what a
           'level' means in terms of spaces or other characters
           output.) Used internally in recursive calls while
           pretty-printing.

        :param eventual_encoding: The tag is destined to be
           encoded into this encoding. decode_contents() is _not_
           responsible for performing that encoding. This information
           is passed in so that it can be substituted in if the
           document contains a <META> tag that mentions the document's
           encoding.

        :param formatter: A Formatter object, or a string naming one of
            the standard Formatters.

        """
        return self.decode(
            indent_level,
            eventual_encoding,
            formatter,
            iterator=self.descendants,
        )

    def encode_contents(
        self,
        indent_level=None,
        encoding=DEFAULT_OUTPUT_ENCODING,
        formatter="minimal",
    ):
        """Renders the contents of this PageElement as a bytestring.

        :param indent_level: Each line of the rendering will be
           indented this many levels. (The formatter decides what a
           'level' means in terms of spaces or other characters
           output.) Used internally in recursive calls while
           pretty-printing.

        :param eventual_encoding: The bytestring will be in this encoding.

        :param formatter: A Formatter object, or a string naming one of
            the standard Formatters.

        :return: A bytestring.
        """
        contents = self.decode_contents(indent_level, encoding, formatter)
        return contents.encode(encoding)

    # Soup methods

    def find(self, name=None, attrs={}, recursive=True, string=None, **kwargs):
        """Look in the children of this PageElement and find the first
        PageElement that matches the given criteria.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param recursive: If this is True, find() will perform a
            recursive search of this PageElement's children. Otherwise,
            only the direct children will be considered.
        :param limit: Stop looking after finding this many results.
        :kwargs: A dictionary of filters on attribute values.
        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        results = self.find_all(
            name,
            attrs,
            recursive,
            string,
            1,
            _stacklevel=3,
            **kwargs,
        )
        element = results[0] if results else None
        return element

    def find_all(
        self,
        name=None,
        attrs={},
        recursive=True,
        string=None,
        limit=None,
        **kwargs,
    ):  # -> ResultSet:
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

    # Generator methods

    @property
    def children(self):
        """Iterate over all direct children of this PageElement.

        :yield: A sequence of PageElements.
        """
        # return iter() to make the purpose of the method clear
        return iter(self.contents)  # XXX This seems to be untested.

    @property
    def self_and_descendants(self):
        """Iterate over this PageElement and its children in a
        breadth-first sequence.

        :yield: A sequence of PageElements.
        """
        if not self.hidden:
            yield self
        yield from self.descendants

    @property
    def descendants(self):
        """Iterate over all children of this PageElement in a
        breadth-first sequence.

        :yield: A sequence of PageElements.
        """
        if not len(self.contents):
            return
        stopNode = self._last_descendant().next_element
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next_element

    # CSS selector code
    def select_one(self, selector, namespaces=None, **kwargs):
        """Perform a CSS selection operation on the current element.

        :param selector: A CSS selector.

        :param namespaces: A dictionary mapping namespace prefixes
           used in the CSS selector to namespace URIs. By default,
           Bisque will use the prefixes it encountered while
           parsing the document.

        :param kwargs: Keyword arguments to be passed into Chinois's
           chinois.select() method.

        :return: A Tag.
        :rtype: bisque.element.Tag
        """
        return self.css.select_one(selector, namespaces, **kwargs)

    def select(self, selector, namespaces=None, limit=None, **kwargs):
        """Perform a CSS selection operation on the current element.

        This uses the SoupSieve library.

        :param selector: A string containing a CSS selector.

        :param namespaces: A dictionary mapping namespace prefixes
           used in the CSS selector to namespace URIs. By default,
           Bisque will use the prefixes it encountered while
           parsing the document.

        :param limit: After finding this number of results, stop looking.

        :param kwargs: Keyword arguments to be passed into SoupSieve's
           chinois.select() method.

        :return: A ResultSet of Tags.
        :rtype: bisque.element.ResultSet
        """
        return self.css.select(selector, namespaces, limit, **kwargs)

    @property
    def css(self):
        """Return an interface to the CSS selector API."""
        return CSS(self)

    # Old names for backwards compatibility
    def childGenerator(self):
        """Deprecated generator."""
        return self.children

    def recursiveChildGenerator(self):
        """Deprecated generator."""
        return self.descendants

    def has_key(self, key):
        """Deprecated method. This was kind of misleading because has_key()
        (attributes) was different from __in__ (contents).

        has_key() is gone in Python 3, anyway.
        """
        warnings.warn(
            "has_key is deprecated. Use has_attr(key) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.has_attr(key)
