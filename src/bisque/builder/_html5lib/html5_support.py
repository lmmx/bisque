import warnings

import html5lib

from bisque.builder.core.features import HTML, HTML_5, PERMISSIVE
from bisque.builder.core.html_builder import HTMLTreeBuilder
from bisque.builder.core.parser_names import HTML5LIB
from bisque.builder.core.xml import DetectsXMLParsedAsHTML
from bisque.models import StrTypes

from .main import TreeBuilderForHtml5lib

__all__ = ["HTML5TreeBuilder"]


class HTML5TreeBuilder(HTMLTreeBuilder):
    """Use html5lib to build a tree.

    Note that this TreeBuilder does not support some features common
    to HTML TreeBuilders. Some of these features could theoretically
    be implemented, but at the very least it's quite difficult,
    because html5lib moves the parse tree around as it's being built.

    * This TreeBuilder doesn't use different subclasses of NavigableString
      based on the name of the tag in which the string was found.

    * You can't use a SoupStrainer to parse only part of a document.
    """

    NAME = HTML5LIB

    features = [NAME, PERMISSIVE, HTML_5, HTML]

    # html5lib can tell us which line number and position in the
    # original file is the source of an element.
    TRACKS_LINE_NUMBERS = True

    def prepare_markup(
        self,
        markup,
        user_specified_encoding,
        document_declared_encoding=None,
        exclude_encodings=None,
    ):
        # Store the user-specified encoding for use later on.
        self.user_specified_encoding = user_specified_encoding

        # document_declared_encoding and exclude_encodings aren't used
        # ATM because the html5lib TreeBuilder doesn't use
        # UnicodeDammit.
        if exclude_encodings:
            warnings.warn(
                "You provided a value for exclude_encoding, but the html5lib tree builder doesn't support exclude_encoding.",
                stacklevel=3,
            )

        # html5lib only parses HTML, so if it's given XML that's worth
        # noting.
        DetectsXMLParsedAsHTML.warn_if_markup_looks_like_xml(markup)

        yield (markup, None, None, False)

    # These methods are defined by Bisque.
    def feed(self, markup):
        if self.soup.parse_only is not None:
            warnings.warn(
                "You provided a value for parse_only, but the html5lib tree builder doesn't support parse_only. The entire document will be parsed.",
                stacklevel=4,
            )
        parser = html5lib.HTMLParser(tree=self.create_treebuilder)
        self.underlying_builder.parser = parser
        extra_kwargs = dict()
        if not isinstance(markup, StrTypes):
            extra_kwargs["override_encoding"] = self.user_specified_encoding
        doc = parser.parse(markup, **extra_kwargs)

        # Set the character encoding detected by the tokenizer.
        if isinstance(markup, StrTypes):
            # We need to special-case this because html5lib sets
            # charEncoding to UTF-8 if it gets Unicode input.
            doc.original_encoding = None
        else:
            original_encoding = parser.tokenizer.stream.charEncoding[0]
            if not isinstance(original_encoding, StrTypes):
                # In 0.99999999 and up, the encoding is an html5lib
                # Encoding object. We want to use a string for compatibility
                # with other tree builders.
                original_encoding = original_encoding.name
            doc.original_encoding = original_encoding
        self.underlying_builder.parser = None

    def create_treebuilder(self, namespaceHTMLElements):
        self.underlying_builder = TreeBuilderForHtml5lib(
            namespaceHTMLElements,
            self.soup,
            store_line_numbers=self.store_line_numbers,
        )
        return self.underlying_builder

    def test_fragment_to_document(self, fragment):
        """See `TreeBuilder`."""
        return "<html><head></head><body>%s</body></html>" % fragment
