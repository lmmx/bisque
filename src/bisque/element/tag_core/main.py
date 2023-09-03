from __future__ import annotations

from typing import ClassVar

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
    "..."


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
