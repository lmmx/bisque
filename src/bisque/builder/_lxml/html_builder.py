from lxml import etree

from bisque.builder.core.features import FAST, HTML, PERMISSIVE
from bisque.builder.core.html_builder import HTMLTreeBuilder
from bisque.builder.core.main import ParserRejectedMarkup
from bisque.builder.core.parser_names import LXML, LXML_HTML
from bisque.element import ProcessingInstruction

from .xml_builder import LXMLTreeBuilderForXML

__all__ = ["LXMLTreeBuilder"]


class LXMLTreeBuilder(HTMLTreeBuilder, LXMLTreeBuilderForXML):
    NAME = LXML
    ALTERNATE_NAMES = [LXML_HTML]

    features = ALTERNATE_NAMES + [NAME, HTML, FAST, PERMISSIVE]
    is_xml = False
    processing_instruction_class = ProcessingInstruction

    def default_parser(self, encoding):
        return etree.HTMLParser

    def feed(self, markup):
        encoding = self.soup.original_encoding
        try:
            self.parser = self.parser_for(encoding)
            self.parser.feed(markup)
            self.parser.close()
        except (UnicodeDecodeError, LookupError, etree.ParserError) as e:
            raise ParserRejectedMarkup(e)

    def test_fragment_to_document(self, fragment):
        """See `TreeBuilder`."""
        return "<html><body>%s</body></html>" % fragment
