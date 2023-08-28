"""
Sets a single method `set_up_substitutions` and 5 class variables
(`empty_element_tags`, `block_elements`, `DEFAULT_STRING_CONTAINERS`,
`DEFAULT_PRESERVE_WHITESPACE_TAGS`, `DEFAULT_CDATA_LIST_ATTRIBUTES`).
"""
from bisque.element import (
    CharsetMetaAttributeValue,
    ContentMetaAttributeValue,
    RubyParenthesisString,
    RubyTextString,
    Script,
    Stylesheet,
    TemplateString,
)

from .main import TreeBuilder

__all__ = ["HTMLTreeBuilder"]


class HTMLTreeBuilder(TreeBuilder):
    """This TreeBuilder knows facts about HTML.

    Such as which tags are empty-element tags.
    """

    empty_element_tags = {
        # These are from HTML5.
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "keygen",
        "link",
        "menuitem",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
        # These are from earlier versions of HTML and are removed in HTML5.
        "basefont",
        "bgsound",
        "command",
        "frame",
        "image",
        "isindex",
        "nextid",
        "spacer",
    }
    # The HTML standard defines these as block-level elements. Beautiful
    # Soup does not treat these elements differently from other elements,
    # but it may do so eventually, and this information is available if
    # you need to use it.
    block_elements = {
        "address",
        "article",
        "aside",
        "blockquote",
        "canvas",
        "dd",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "noscript",
        "ol",
        "output",
        "p",
        "pre",
        "section",
        "table",
        "tfoot",
        "ul",
        "video",
    }
    # These HTML tags need special treatment so they can be
    # represented by a string class other than NavigableString.
    #
    # For some of these tags, it's because the HTML standard defines
    # an unusual content model for them. I made this list by going
    # through the HTML spec
    # (https://html.spec.whatwg.org/#metadata-content) and looking for
    # "metadata content" elements that can contain strings.
    #
    # The Ruby tags (<rt> and <rp>) are here despite being normal
    # "phrasing content" tags, because the content they contain is
    # qualitatively different from other text in the document, and it
    # can be useful to be able to distinguish it.
    #
    # TODO: Arguably <noscript> could go here but it seems
    # qualitatively different from the other tags.
    DEFAULT_STRING_CONTAINERS = {
        "rt": RubyTextString,
        "rp": RubyParenthesisString,
        "style": Stylesheet,
        "script": Script,
        "template": TemplateString,
    }
    # The HTML standard defines these attributes as containing a
    # space-separated list of values, not a single value. That is,
    # class="foo bar" means that the 'class' attribute has two values,
    # 'foo' and 'bar', not the single value 'foo bar'.  When we
    # encounter one of these attributes, we will parse its value into
    # a list of values if possible. Upon output, the list will be
    # converted back into a string.
    DEFAULT_CDATA_LIST_ATTRIBUTES = {
        "*": ["class", "accesskey", "dropzone"],
        "a": ["rel", "rev"],
        "link": ["rel", "rev"],
        "td": ["headers"],
        "th": ["headers"],
        "form": ["accept-charset"],
        "object": ["archive"],
        # These are HTML5 specific, as are *.accesskey and *.dropzone above.
        "area": ["rel"],
        "icon": ["sizes"],
        "iframe": ["sandbox"],
        "output": ["for"],
    }
    DEFAULT_PRESERVE_WHITESPACE_TAGS = {"pre", "textarea"}

    def set_up_substitutions(self, tag):
        """Replace the declared encoding in a <meta> tag with a placeholder,
        to be substituted when the tag is output to a string.

        An HTML document may come in to Bisque as one
        encoding, but exit in a different encoding, and the <meta> tag
        needs to be changed to reflect this.

        :param tag: A `Tag`
        :return: Whether or not a substitution was performed.
        """
        # We are only interested in <meta> tags
        if tag.name != "meta":
            return False
        http_equiv = tag.get("http-equiv")
        content = tag.get("content")
        charset = tag.get("charset")
        # We are interested in <meta> tags that say what encoding the
        # document was originally in. This means HTML 5-style <meta>
        # tags that provide the "charset" attribute. It also means
        # HTML 4-style <meta> tags that provide the "content"
        # attribute and have "http-equiv" set to "content-type".
        #
        # In both cases we will replace the value of the appropriate
        # attribute with a standin object that can take on any
        # encoding.
        meta_encoding = None
        if charset is not None:
            # HTML 5 style:
            # <meta charset="utf8">
            meta_encoding = charset
            tag["charset"] = CharsetMetaAttributeValue(original_value=charset)
        elif (
            content is not None
            and http_equiv is not None
            and http_equiv.lower() == "content-type"
        ):
            # HTML 4 style:
            # <meta http-equiv="content-type" content="text/html; charset=utf8">
            tag["content"] = ContentMetaAttributeValue(original_value=content)
        return meta_encoding is not None
