from __future__ import annotations

import warnings

from bisque.css import CSS

from ..attributes import AttributeValueWithCharsetSubstitution
from ..encodings import DEFAULT_OUTPUT_ENCODING

__all__ = ["TagBase"]


class TagBase:
    """Standalone methods and attributes for Tag.

    Represents an HTML or XML tag that is part of a parse tree, along
    with its attributes and contents.

    When Bisque parses the markup <b>penguin</b>, it will
    create a Tag object representing the <b> tag.
    """

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
        can_be_empty_element=None,
        cdata_list_attributes=None,
        preserve_whitespace_tags=None,
        interesting_string_types=None,
        namespaces=None,
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
        if parser is None:
            self.parser_class = None
        else:
            # We don't actually store the parser object: that lets extracted
            # chunks be garbage-collected.
            self.parser_class = parser.__class__
        if name is None:
            raise ValueError("No value provided for new tag's name.")
        self.name = name
        self.namespace = namespace
        self._namespaces = namespaces or {}
        self.prefix = prefix
        if (not builder or builder.store_line_numbers) and (
            sourceline is not None or sourcepos is not None
        ):
            self.sourceline = sourceline
            self.sourcepos = sourcepos
        if attrs is None:
            attrs = {}
        elif attrs:
            if builder is not None and builder.cdata_list_attributes:
                attrs = builder._replace_cdata_list_attribute_values(self.name, attrs)
            else:
                attrs = dict(attrs)
        else:
            attrs = dict(attrs)

        # If possible, determine ahead of time whether this tag is an
        # XML tag.
        if builder:
            self.known_xml = builder.is_xml
        else:
            self.known_xml = is_xml
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False

        if builder is None:
            # In the absence of a TreeBuilder, use whatever values were
            # passed in here. They're probably None, unless this is a copy of some
            # other tag.
            self.can_be_empty_element = can_be_empty_element
            self.cdata_list_attributes = cdata_list_attributes
            self.preserve_whitespace_tags = preserve_whitespace_tags
            self.interesting_string_types = interesting_string_types
        else:
            # Set up any substitutions for this tag, such as the charset in a META tag.
            builder.set_up_substitutions(self)

            # Ask the TreeBuilder whether this tag might be an empty-element tag.
            self.can_be_empty_element = builder.can_be_empty_element(name)

            # Keep track of the list of attributes of this tag that
            # might need to be treated as a list.
            #
            # For performance reasons, we store the whole data structure
            # rather than asking the question of every tag. Asking would
            # require building a new data structure every time, and
            # (unlike can_be_empty_element), we almost never need
            # to check this.
            self.cdata_list_attributes = builder.cdata_list_attributes

            # Keep track of the names that might cause this tag to be treated as a
            # whitespace-preserved tag.
            self.preserve_whitespace_tags = builder.preserve_whitespace_tags

            if self.name in builder.string_containers:
                # This sort of tag uses a special string container
                # subclass for most of its strings. When we ask the
                self.interesting_string_types = builder.string_containers[self.name]
            else:
                self.interesting_string_types = self.DEFAULT_INTERESTING_STRING_TYPES

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

    def decompose(self):
        """Recursively destroys this PageElement and its children.

        This element will be removed from the tree and wiped out; so
        will everything beneath it.

        The behavior of a decomposed PageElement is undefined and you
        should never use one for anything, but if you need to _check_
        whether an element has been decomposed, you can use the
        `decomposed` property.
        """
        self.extract()
        i = self
        while i is not None:
            n = i.next_element
            i.__dict__.clear()
            i.contents = []
            i._decomposed = True
            i = n

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
        if len(tag) > 3 and tag.endswith("Tag"):
            # BS3: soup.aTag -> "soup.find("a")
            tag_name = tag[:-3]
            warnings.warn(
                '.%(name)sTag is deprecated, use .find("%(name)s") instead. If you really were looking for a tag called %(name)sTag, use .find("%(name)sTag")'
                % dict(name=tag_name),
                DeprecationWarning,
                stacklevel=2,
            )
            return self.find(tag_name)
        # We special case contents to avoid recursion.
        elif not tag.startswith("__") and not tag == "contents":
            return self.find(tag)
        raise AttributeError(
            f"'{self.__class__}' object has no attribute '{tag}'",
        )

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

    # Names for the different events yielded by _event_stream
    START_ELEMENT_EVENT = object()
    END_ELEMENT_EVENT = object()
    EMPTY_ELEMENT_EVENT = object()
    STRING_ELEMENT_EVENT = object()

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