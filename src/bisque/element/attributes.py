from __future__ import annotations

import re
from typing import ClassVar

from pydantic import Field, model_validator

from ..models import StrRecord, StrRoot
from .encodings import PYTHON_SPECIFIC_ENCODINGS

__all__ = [
    "NamespacedAttribute",
    "AttributeValueWithCharsetSubstitution",
    "CharsetMetaAttributeValue",
    "ContentMetaAttributeValue",
]


class NamespacedAttribute(StrRecord):
    """A namespaced string (e.g. 'xml:lang') that remembers the namespace
    ('xml') and the name ('lang') that were used to create it.
    """

    prefix: str | None
    name: str | None = Field(
        None,
        description="""This is the default namespace. Its name "has no value"
                       per https://www.w3.org/TR/xml-names/#defaulting""",
    )
    namespace: str | None = None

    def __str__(self) -> str:
        return ":".join(filter(None, [self.prefix, self.name]))


class AttributeValueWithCharsetSubstitution(StrRecord):
    """A stand-in object for a character encoding specified in HTML."""


class CharsetMetaAttributeValue(AttributeValueWithCharsetSubstitution):
    """A generic stand-in for the value of a meta tag's 'charset' attribute.

    When Bisque parses the markup '<meta charset="utf8">', the
    value of the 'charset' attribute will be one of these objects.
    """

    original_value: str

    def encode(self, encoding):
        """When an HTML document is being encoded to a given encoding, the
        value of a meta tag's 'charset' is the name of the encoding.
        """
        return "" if encoding in PYTHON_SPECIFIC_ENCODINGS else encoding


class ContentMetaAttributeValue(AttributeValueWithCharsetSubstitution):
    """A generic stand-in for the value of a meta tag's 'content' attribute.

    When Bisque parses the markup:
     <meta http-equiv="content-type" content="text/html; charset=utf8">

    The value of the 'content' attribute will be one of these objects.
    """

    original_value: str

    CHARSET_RE: ClassVar[re.Pattern] = re.compile(r"((^|;)\s*charset=)([^;]*)", re.M)

    @model_validator(mode="after")
    def _choose_str_type(
        cls,
        self: ContentMetaAttributeValue,
    ) -> StrRoot | ContentMetaAttributeValue:
        matched = self.CHARSET_RE.search(self.original_value) is not None
        # If not matched, no substitution necessary.
        return self if matched else StrRoot(self.original_value)

    def encode(self, encoding):
        if encoding in PYTHON_SPECIFIC_ENCODINGS:
            return ""

        def rewrite(matched: re.Match):
            return matched.group(1) + encoding

        return self.CHARSET_RE.sub(rewrite, self.original_value)
