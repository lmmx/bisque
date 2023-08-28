import re
import warnings

__all__ = ["DetectsXMLParsedAsHTML", "XMLParsedAsHTMLWarning"]


class XMLParsedAsHTMLWarning(UserWarning):
    """The warning issued when an HTML parser is used to parse
    XML that is not XHTML.
    """

    MESSAGE = """It looks like you're parsing an XML document using an HTML parser. If this really is an HTML document (maybe it's XHTML?), you can ignore or filter this warning. If it's XML, you should know that using an XML parser will be more reliable. To parse this document as XML, make sure you have the lxml package installed, and pass the keyword argument `features="xml"` into the Bisque constructor."""


class DetectsXMLParsedAsHTML:
    """A mixin class for any class (a TreeBuilder, or some class used by a
    TreeBuilder) that's in a position to detect whether an XML
    document is being incorrectly parsed as HTML, and issue an
    appropriate warning.

    This requires being able to observe an incoming processing
    instruction that might be an XML declaration, and also able to
    observe tags as they're opened. If you can't do that for a given
    TreeBuilder, there's a less reliable implementation based on
    examining the raw markup.
    """

    # Regular expression for seeing if markup has an <html> tag.
    LOOKS_LIKE_HTML = re.compile("<[^ +]html", re.I)
    LOOKS_LIKE_HTML_B = re.compile(b"<[^ +]html", re.I)

    XML_PREFIX = "<?xml"
    XML_PREFIX_B = b"<?xml"

    @classmethod
    def warn_if_markup_looks_like_xml(cls, markup):
        """Perform a check on some markup to see if it looks like XML
        that's not XHTML. If so, issue a warning.

        This is much less reliable than doing the check while parsing,
        but some of the tree builders can't do that.

        :return: True if the markup looks like non-XHTML XML, False
        otherwise.
        """
        if isinstance(markup, bytes):
            prefix = cls.XML_PREFIX_B
            looks_like_html = cls.LOOKS_LIKE_HTML_B
        else:
            prefix = cls.XML_PREFIX
            looks_like_html = cls.LOOKS_LIKE_HTML

        if (
            markup is not None
            and markup.startswith(prefix)
            and not looks_like_html.search(markup[:500])
        ):
            cls._warn()
            return True
        return False

    @classmethod
    def _warn(cls):
        """Issue a warning about XML being parsed as HTML."""
        warnings.warn(XMLParsedAsHTMLWarning.MESSAGE, XMLParsedAsHTMLWarning)

    def _initialize_xml_detector(self):
        """Call this method before parsing a document."""
        self._first_processing_instruction = None
        self._root_tag = None

    def _document_might_be_xml(self, processing_instruction):
        """Call this method when encountering an XML declaration, or a
        "processing instruction" that might be an XML declaration.
        """
        if self._first_processing_instruction is not None or self._root_tag is not None:
            # The document has already started. Don't bother checking
            # anymore.
            return

        self._first_processing_instruction = processing_instruction

        # We won't know until we encounter the first tag whether or
        # not this is actually a problem.

    def _root_tag_encountered(self, name):
        """Call this when you encounter the document's root tag.

        This is where we actually check whether an XML document is
        being incorrectly parsed as HTML, and issue the warning.
        """
        if self._root_tag is not None:
            # This method was incorrectly called multiple times. Do
            # nothing.
            return

        self._root_tag = name
        if (
            name != "html"
            and self._first_processing_instruction is not None
            and self._first_processing_instruction.lower().startswith("xml ")
        ):
            # We encountered an XML declaration and then a tag other
            # than 'html'. This is a reliable indicator that a
            # non-XHTML document is being parsed as XML.
            self._warn()
