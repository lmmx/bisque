from __future__ import annotations

import warnings
from collections.abc import Callable

from .attributes import (
    AttributeValueWithCharsetSubstitution,
    CharsetMetaAttributeValue,
    ContentMetaAttributeValue,
    NamespacedAttribute,
)
from .encodings import DEFAULT_OUTPUT_ENCODING, PYTHON_SPECIFIC_ENCODINGS
from .tag_core import (
    CData,
    Comment,
    Declaration,
    Doctype,
    NavigableString,
    PageElement,
    PreformattedString,
    ProcessingInstruction,
    ResultSet,
    RubyParenthesisString,
    RubyTextString,
    Script,
    SoupStrainer,
    Stylesheet,
    Tag,
    TemplateString,
    XMLProcessingInstruction,
)
from .whitespace import nonwhitespace_re, whitespace_re

__all__ = [
    "AttributeValueWithCharsetSubstitution",
    "CharsetMetaAttributeValue",
    "ContentMetaAttributeValue",
    "NamespacedAttribute",
    "PageElement",
    "DEFAULT_OUTPUT_ENCODING",
    "PYTHON_SPECIFIC_ENCODINGS",
    "ResultSet",
    "SoupStrainer",
    "Tag",
    "CData",
    "Comment",
    "Declaration",
    "Doctype",
    "NavigableString",
    "PreformattedString",
    "ProcessingInstruction",
    "RubyParenthesisString",
    "RubyTextString",
    "Script",
    "Stylesheet",
    "TemplateString",
    "XMLProcessingInstruction",
    "nonwhitespace_re",
    "whitespace_re",
]
