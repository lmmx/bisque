from __future__ import annotations

from collections.abc import Callable

from bisque.formatter import Formatter, HTMLFormatter, XMLFormatter

__all__ = ["PageElementBase"]


class PageElementBase:
    """Standalone methods and attributes for PageElement.

    Contains the navigational information for some part of the page:
    that is, its current location in the parse tree.

    NavigableString, Tag, etc. are all subclasses of PageElement.
    """

    # In general, we can't tell just by looking at an element whether
    # it's contained in an XML document or an HTML document. But for
    # Tags (q.v.) we can store this information at parse time.
    known_xml = None

    def setup(
        self,
        parent=None,
        previous_element=None,
        next_element=None,
        previous_sibling=None,
        next_sibling=None,
    ):
        """Sets up the initial relations between this element and
        other elements.

        :param parent: The parent of this element.

        :param previous_element: The element parsed immediately before
            this one.

        :param next_element: The element parsed immediately before
            this one.

        :param previous_sibling: The most recently encountered element
            on the same level of the parse tree as this one.

        :param previous_sibling: The next element to be encountered
            on the same level of the parse tree as this one.
        """
        self.parent = parent

        self.previous_element = previous_element
        if previous_element is not None:
            self.previous_element.next_element = self

        self.next_element = next_element
        if self.next_element is not None:
            self.next_element.previous_element = self

        self.next_sibling = next_sibling
        if self.next_sibling is not None:
            self.next_sibling.previous_sibling = self

        if (
            previous_sibling is None
            and self.parent is not None
            and self.parent.contents
        ):
            previous_sibling = self.parent.contents[-1]

        self.previous_sibling = previous_sibling
        if previous_sibling is not None:
            self.previous_sibling.next_sibling = self

    def format_string(self, s, formatter):
        """Format the given string using the given formatter.

        :param s: A string.
        :param formatter: A Formatter object, or a string naming one of the standard formatters.
        """
        if formatter is None:
            return s
        if not isinstance(formatter, Formatter):
            formatter = self.formatter_for_name(formatter)
        output = formatter.substitute(s)
        return output

    def formatter_for_name(self, formatter):
        """Look up or create a Formatter for the given identifier,
        if necessary.

        :param formatter: Can be a Formatter object (used as-is), a
            function (used as the entity substitution hook for an
            XMLFormatter or HTMLFormatter), or a string (used to look
            up an XMLFormatter or HTMLFormatter in the appropriate
            registry.
        """
        if isinstance(formatter, Formatter):
            return formatter
        if self._is_xml:
            c = XMLFormatter
        else:
            c = HTMLFormatter
        if isinstance(formatter, Callable):
            return c(entity_substitution=formatter)
        return c.REGISTRY[formatter]

    @property
    def _is_xml(self):
        """Is this element part of an XML tree or an HTML tree?

        This is used in formatter_for_name, when deciding whether an
        XMLFormatter or HTMLFormatter is more appropriate. It can be
        inefficient, but it should be called very rarely.
        """
        if self.known_xml is not None:
            # Most of the time we will have determined this when the
            # document is parsed.
            return self.known_xml

        # Otherwise, it's likely that this element was created by
        # direct invocation of the constructor from within the user's
        # Python code.
        if self.parent is None:
            # This is the top-level object. It should have .known_xml set
            # from tree creation. If not, take a guess--BS is usually
            # used on HTML markup.
            return getattr(self, "is_xml", False)
        return self.parent._is_xml

    default = object()

    def _all_strings(self, strip=False, types=default):
        """Yield all strings of certain classes, possibly stripping them.

        This is implemented differently in Tag and NavigableString.
        """
        raise NotImplementedError()

    @property
    def stripped_strings(self):
        """Yield all strings in this PageElement, stripping them first.

        :yield: A sequence of stripped strings.
        """
        yield from self._all_strings(True)

    def get_text(self, separator="", strip=False, types=default):
        """Get all child strings of this PageElement, concatenated using the
        given separator.

        :param separator: Strings will be concatenated using this separator.

        :param strip: If True, strings will be stripped before being
            concatenated.

        :param types: A tuple of NavigableString subclasses. Any
            strings of a subclass not found in this list will be
            ignored. Although there are exceptions, the default
            behavior in most cases is to consider only NavigableString
            and CData objects. That means no comments, processing
            instructions, etc.

        :return: A string.
        """
        return separator.join([s for s in self._all_strings(strip, types=types)])

    getText = get_text
    text = property(get_text)

    def replace_with(self, *args):
        """Replace this PageElement with one or more PageElements, keeping the
        rest of the tree the same.

        :param args: One or more PageElements.
        :return: `self`, no longer part of the tree.
        """
        if self.parent is None:
            raise ValueError(
                "Cannot replace one element with another when the "
                "element to be replaced is not part of a tree.",
            )
        if len(args) == 1 and args[0] is self:
            return
        if any(x is self.parent for x in args):
            raise ValueError("Cannot replace a Tag with its parent.")
        old_parent = self.parent
        my_index = self.parent.index(self)
        self.extract(_self_index=my_index)
        for idx, replace_with in enumerate(args, start=my_index):
            old_parent.insert(idx, replace_with)
        return self

    def unwrap(self):
        """Replace this PageElement with its contents.

        :return: `self`, no longer part of the tree.
        """
        my_parent = self.parent
        if self.parent is None:
            raise ValueError(
                "Cannot replace an element with its contents when that"
                "element is not part of a tree.",
            )
        my_index = self.parent.index(self)
        self.extract(_self_index=my_index)
        for child in reversed(self.contents[:]):
            my_parent.insert(my_index, child)
        return self

    replace_with_children = unwrap

    def wrap(self, wrap_inside):
        """Wrap this PageElement inside another one.

        :param wrap_inside: A PageElement.
        :return: `wrap_inside`, occupying the position in the tree that used
           to be occupied by `self`, and with `self` inside it.
        """
        me = self.replace_with(wrap_inside)
        wrap_inside.append(me)
        return wrap_inside

    def extract(self, _self_index=None):
        """Destructively rips this element out of the tree.

        :param _self_index: The location of this element in its parent's
           .contents, if known. Passing this in allows for a performance
           optimization.

        :return: `self`, no longer part of the tree.
        """
        if self.parent is not None:
            if _self_index is None:
                _self_index = self.parent.index(self)
            del self.parent.contents[_self_index]

        # Find the two elements that would be next to each other if
        # this element (and any children) hadn't been parsed. Connect
        # the two.
        last_child = self._last_descendant()
        next_element = last_child.next_element

        if (
            self.previous_element is not None
            and self.previous_element is not next_element
        ):
            self.previous_element.next_element = next_element
        if next_element is not None and next_element is not self.previous_element:
            next_element.previous_element = self.previous_element
        self.previous_element = None
        last_child.next_element = None

        self.parent = None
        if (
            self.previous_sibling is not None
            and self.previous_sibling is not self.next_sibling
        ):
            self.previous_sibling.next_sibling = self.next_sibling
        if (
            self.next_sibling is not None
            and self.next_sibling is not self.previous_sibling
        ):
            self.next_sibling.previous_sibling = self.previous_sibling
        self.previous_sibling = self.next_sibling = None
        return self

    def append(self, tag):
        """Appends the given PageElement to the contents of this one.

        :param tag: A PageElement.
        """
        self.insert(len(self.contents), tag)

    def find_all_next(self, name=None, attrs={}, string=None, limit=None, **kwargs):
        """Find all PageElements that match the given criteria and appear
        later in the document than this PageElement.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param string: A filter for a NavigableString with specific text.
        :param limit: Stop looking after finding this many results.
        :kwargs: A dictionary of filters on attribute values.
        :return: A ResultSet containing PageElements.
        """
        _stacklevel = kwargs.pop("_stacklevel", 2)
        return self._find_all(
            name,
            attrs,
            string,
            limit,
            self.next_elements,
            _stacklevel=_stacklevel + 1,
            **kwargs,
        )

    def find_next_sibling(self, name=None, attrs={}, string=None, **kwargs):
        """Find the closest sibling to this PageElement that matches the
        given criteria and appears later in the document.

        All find_* methods take a common set of arguments. See the
        online documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param string: A filter for a NavigableString with specific text.
        :kwargs: A dictionary of filters on attribute values.
        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        return self._find_one(self.find_next_siblings, name, attrs, string, **kwargs)

    def find_previous(self, name=None, attrs={}, string=None, **kwargs):
        """Look backwards in the document from this PageElement and find the
        first PageElement that matches the given criteria.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param string: A filter for a NavigableString with specific text.
        :kwargs: A dictionary of filters on attribute values.
        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        return self._find_one(self.find_all_previous, name, attrs, string, **kwargs)

    def find_all_previous(self, name=None, attrs={}, string=None, limit=None, **kwargs):
        """Look backwards in the document from this PageElement and find all
        PageElements that match the given criteria.

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
            self.previous_elements,
            _stacklevel=_stacklevel + 1,
            **kwargs,
        )

    def find_previous_sibling(self, name=None, attrs={}, string=None, **kwargs):
        """Returns the closest sibling to this PageElement that matches the
        given criteria and appears earlier in the document.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param string: A filter for a NavigableString with specific text.
        :kwargs: A dictionary of filters on attribute values.
        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        return self._find_one(
            self.find_previous_siblings,
            name,
            attrs,
            string,
            **kwargs,
        )

    def find_previous_siblings(
        self,
        name=None,
        attrs={},
        string=None,
        limit=None,
        **kwargs,
    ):
        """Returns all siblings to this PageElement that match the
        given criteria and appear earlier in the document.

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
            self.previous_siblings,
            _stacklevel=_stacklevel + 1,
            **kwargs,
        )

    def find_parent(self, name=None, attrs={}, **kwargs):
        """Find the closest parent of this PageElement that matches the given
        criteria.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :kwargs: A dictionary of filters on attribute values.

        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        # NOTE: We can't use _find_one because findParents takes a different
        # set of arguments.
        results = self.find_parents(name, attrs, 1, _stacklevel=3, **kwargs)
        element = results[0] if results else None
        return element

    def find_parents(self, name=None, attrs={}, limit=None, **kwargs):
        """Find all parents of this PageElement that match the given criteria.

        All find_* methods take a common set of arguments. See the online
        documentation for detailed explanations.

        :param name: A filter on tag name.
        :param attrs: A dictionary of filters on attribute values.
        :param limit: Stop looking after finding this many results.
        :kwargs: A dictionary of filters on attribute values.

        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        _stacklevel = kwargs.pop("_stacklevel", 2)
        return self._find_all(
            name,
            attrs,
            None,
            limit,
            self.parents,
            _stacklevel=_stacklevel + 1,
            **kwargs,
        )

    @property
    def next(self):
        """The PageElement, if any, that was parsed just after this one.

        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        return self.next_element

    @property
    def previous(self):
        """The PageElement, if any, that was parsed just before this one.

        :return: A PageElement.
        :rtype: bisque.element.Tag | bisque.element.NavigableString
        """
        return self.previous_element

    # These methods do the real heavy lifting.

    def _find_one(self, method, name, attrs, string, **kwargs):
        results = method(name, attrs, string, 1, _stacklevel=4, **kwargs)
        element = results[0] if results else None
        return element

    # These generators can be used to navigate starting from both
    # NavigableStrings and Tags.
    @property
    def next_elements(self):
        """All PageElements that were parsed after this one.

        :yield: A sequence of PageElements.
        """
        i = self.next_element
        while i is not None:
            yield i
            i = i.next_element

    @property
    def next_siblings(self):
        """All PageElements that are siblings of this one but were parsed
        later.

        :yield: A sequence of PageElements.
        """
        i = self.next_sibling
        while i is not None:
            yield i
            i = i.next_sibling

    @property
    def previous_elements(self):
        """All PageElements that were parsed before this one.

        :yield: A sequence of PageElements.
        """
        i = self.previous_element
        while i is not None:
            yield i
            i = i.previous_element

    @property
    def previous_siblings(self):
        """All PageElements that are siblings of this one but were parsed
        earlier.

        :yield: A sequence of PageElements.
        """
        i = self.previous_sibling
        while i is not None:
            yield i
            i = i.previous_sibling

    @property
    def parents(self):
        """All PageElements that are parents of this PageElement.

        :yield: A sequence of PageElements.
        """
        i = self.parent
        while i is not None:
            yield i
            i = i.parent

    @property
    def decomposed(self):
        """Check whether a PageElement has been decomposed.

        :rtype: bool
        """
        return getattr(self, "_decomposed", False) or False
