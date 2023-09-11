from __future__ import annotations

from typing import Iterator

from pydantic import Field

from ....models import Element, StrRecord
from ...sentinels import DEFAULT_TYPES_SENTINEL

__all__ = ["BaseNavigableString"]


class BaseNavigableString(StrRecord, validate_assignment=True):
    """A Python Unicode string that is part of a parse tree.

    When Bisque parses the markup <b>penguin</b>, it will
    create a NavigableString for the string "penguin".
    """

    value: str

    parent: Element | None = Field(None, repr=False)
    previous_element: Element | None = Field(None, repr=False)
    next_element: Element | None = Field(None, repr=False)
    previous_sibling: Element | None = Field(None, repr=False)
    next_sibling: Element | None = Field(None, repr=False)
    contents: list[Element] = Field([], repr=False)
    decomposed: bool = Field(False, repr=False)

    PREFIX: str = ""
    SUFFIX: str = ""

    def __init__(self, value: str, **kwargs) -> None:
        super().__init__(value=value, **kwargs)
        self.setup()
        return

    def clear(self) -> None:
        self.__dict__.clear()

    def __deepcopy__(self, memo={}, recursive=False):
        """A copy of a NavigableString has the same contents and class
        as the original, but it is not connected to the parse tree.

        :param recursive: This parameter is ignored; it's only defined
           so that NavigableString.__deepcopy__ implements the same
           signature as Tag.__deepcopy__.
        """
        return self.model_validate(self.model_dump())

    def __copy__(self):
        """A copy of a NavigableString can only be a deep copy, because
        only one PageElement can occupy a given place in a parse tree.
        """
        return self.__deepcopy__()

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
                f"{self.__class__.__name__!r} object has no attribute {attr!r}",
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

    def _all_strings(self, strip=False, types=DEFAULT_TYPES_SENTINEL) -> Iterator[str]:
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
        if types is DEFAULT_TYPES_SENTINEL:
            # Subclasses of this class
            types = (self.TYPE_TABLE.NavigableString, self.TYPE_TABLE.CData)

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

        if strip:
            clone = self.model_copy()
            clone.value = self.value.strip()
            returnable = clone
        else:
            returnable = self
        if len(returnable.value) > 0:
            yield returnable

    strings = property(_all_strings)
