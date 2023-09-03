"""Tests of classes in element.py.

The really big classes -- Tag, PageElement, and NavigableString --
are tested in separate files.
"""

from bisque.element import (
    CharsetMetaAttributeValue,
    ContentMetaAttributeValue,
    NamespacedAttribute,
)

from . import SoupTest


class TestNamedspacedAttribute:
    def test_name_may_be_none_or_missing(self):
        a = NamespacedAttribute(prefix="xmlns", name=None)
        assert a == "xmlns"

        a = NamespacedAttribute(prefix="xmlns", name="")
        assert a == "xmlns"

        a = NamespacedAttribute(prefix="xmlns")
        assert a == "xmlns"

    def test_namespace_may_be_none_or_missing(self):
        a = NamespacedAttribute(prefix=None, name="tag")
        assert a == "tag"

        a = NamespacedAttribute(prefix="", name="tag")
        assert a == "tag"

    def test_attribute_is_equivalent_to_colon_separated_string(self):
        a = NamespacedAttribute(prefix="a", name="b")
        assert "a:b" == a

    def test_attributes_are_equivalent_if_prefix_and_name_identical(self):
        a = NamespacedAttribute(prefix="a", name="b", namespace="c")
        b = NamespacedAttribute(prefix="a", name="b", namespace="c")
        assert a == b

        # The actual namespace is not considered.
        c = NamespacedAttribute(prefix="a", name="b", namespace=None)
        assert a == c

        # But name and prefix are important.
        d = NamespacedAttribute(prefix="a", name="z", namespace="c")
        assert a != d

        e = NamespacedAttribute(prefix="z", name="b", namespace="c")
        assert a != e


class TestAttributeValueWithCharsetSubstitution:
    """Certain attributes are designed to have the charset of the
    final document substituted into their value.
    """

    def test_content_meta_attribute_value(self):
        # The value of a CharsetMetaAttributeValue is whatever
        # encoding the string is in.
        value = CharsetMetaAttributeValue("euc-jp")
        assert "euc-jp" == value
        assert "euc-jp" == value.original_value
        assert "utf8" == value.encode("utf8")
        assert "ascii" == value.encode("ascii")

    def test_content_meta_attribute_value(self):
        value = ContentMetaAttributeValue(original_value="text/html; charset=euc-jp")
        assert "text/html; charset=euc-jp" == value
        assert "text/html; charset=euc-jp" == value.original_value
        assert "text/html; charset=utf8" == value.encode("utf8")
        assert "text/html; charset=ascii" == value.encode("ascii")
