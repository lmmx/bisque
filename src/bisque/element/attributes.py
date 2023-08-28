from __future__ import annotations

import re

from pydantic import Field

from ..models import StrModel
from .encodings import PYTHON_SPECIFIC_ENCODINGS

__all__ = [
    "NamespacedAttribute",
    "AttributeValueWithCharsetSubstitution",
    "CharsetMetaAttributeValue",
    "ContentMetaAttributeValue",
]


class NamespacedAttribute(StrModel):
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


class AttributeValueWithCharsetSubstitution(str):
    """A stand-in object for a character encoding specified in HTML."""


class CharsetMetaAttributeValue(AttributeValueWithCharsetSubstitution):
    """A generic stand-in for the value of a meta tag's 'charset' attribute.

    When Bisque parses the markup '<meta charset="utf8">', the
    value of the 'charset' attribute will be one of these objects.
    """

    def __new__(cls, original_value):
        obj = str.__new__(cls, original_value)
        obj.original_value = original_value
        return obj

    def encode(self, encoding):
        """When an HTML document is being encoded to a given encoding, the
        value of a meta tag's 'charset' is the name of the encoding.
        """
        if encoding in PYTHON_SPECIFIC_ENCODINGS:
            return ""
        return encoding


class ContentMetaAttributeValue(AttributeValueWithCharsetSubstitution):
    """A generic stand-in for the value of a meta tag's 'content' attribute.

    When Bisque parses the markup:
     <meta http-equiv="content-type" content="text/html; charset=utf8">

    The value of the 'content' attribute will be one of these objects.
    """

    CHARSET_RE = re.compile(r"((^|;)\s*charset=)([^;]*)", re.M)

    def __new__(cls, original_value):
        match = cls.CHARSET_RE.search(original_value)
        if match is None:
            # No substitution necessary.
            return str.__new__(str, original_value)

        obj = str.__new__(cls, original_value)
        obj.original_value = original_value
        return obj

    def encode(self, encoding):
        if encoding in PYTHON_SPECIFIC_ENCODINGS:
            return ""

        def rewrite(match):
            return match.group(1) + encoding

        return self.CHARSET_RE.sub(rewrite, self.original_value)
