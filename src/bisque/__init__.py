"""Bisque - A condensed web scraping library.

https://www.github.com/lmmx/bisque

Bisque is adapted from Beautiful Soup under the MIT license.

Bisque uses a pluggable XML or HTML parser to parse a
(possibly invalid) document into a tree representation. Bisque
provides methods and Pythonic idioms that make it easy to navigate,
search, and modify the parse tree.

Like Beautiful Soup, Bisque works with Python 3.6 and up. It works
better if lxml and/or html5lib is installed.

For more than you ever wanted to know about Beautiful Soup, see their
documentation: http://www.crummy.com/software/BeautifulSoup/bs4/doc/
"""

__version__ = "0.3.0"

__all__ = ["Bisque"]

import sys
import warnings
from collections import Counter

from .builder import HTMLParserTreeBuilder
from .builder.core import ParserRejectedMarkup, XMLParsedAsHTMLWarning
from .css import CSS
from .dammit import UnicodeDammit
from .element import (
    DEFAULT_OUTPUT_ENCODING,
    PYTHON_SPECIFIC_ENCODINGS,
    CData,
    Comment,
    Declaration,
    Doctype,
    NavigableString,
    PageElement,
    ProcessingInstruction,
    ResultSet,
    Script,
    SoupStrainer,
    Stylesheet,
    Tag,
    TemplateString,
)
from .main import (
    Bisque,
    FeatureNotFound,
    GuessedAtParserWarning,
    MarkupResemblesLocatorWarning,
    StopParsing,
)

# If this file is run as a script, act as an HTML pretty-printer.
if __name__ == "__main__":
    soup = Bisque(sys.stdin)
    print(soup.prettify())
