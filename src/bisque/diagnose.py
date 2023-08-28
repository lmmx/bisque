"""Diagnostic functions, mainly for use when doing tech support."""

import cProfile
import pstats
import random
import sys
import tempfile
import time
import traceback
from html.parser import HTMLParser
from io import BytesIO

import bisque
from bisque import Bisque, __version__
from bisque.builder import builder_registry

_vowels = "aeiou"
_consonants = "bcdfghjklmnpqrstvwxyz"


def diagnose(data):
    """Diagnostic suite for isolating common problems.

    :param data: A string containing markup that needs to be explained.
    :return: None; diagnostics are printed to standard output.
    """
    print(f"Diagnostic running on Bisque {__version__}")
    print(f"Python version {sys.version}")
    basic_parsers = ["html.parser", "html5lib", "lxml"]
    for name in basic_parsers:
        for builder in builder_registry.builders:
            if name in builder.features:
                break
        else:
            basic_parsers.remove(name)
            print(f"{name} is not installed. Installing it may help.")
    if "lxml" in basic_parsers:
        basic_parsers.append("lxml-xml")
        try:
            from lxml import etree

            print("Found lxml version %s" % ".".join(map(str, etree.LXML_VERSION)))
        except ImportError:
            print("lxml is not installed or couldn't be imported.")
    if "html5lib" in basic_parsers:
        try:
            import html5lib

            print("Found html5lib version %s" % html5lib.__version__)
        except ImportError:
            print("html5lib is not installed or couldn't be imported.")
    if hasattr(data, "read"):
        data = data.read()
    for parser in basic_parsers:
        print("Trying to parse your markup with %s" % parser)
        success = False
        try:
            soup = Bisque(data, features=parser)
            success = True
        except Exception:
            print("%s could not parse the markup." % parser)
            traceback.print_exc()
        if success:
            print("Here's what %s did with the markup:" % parser)
            print(soup.prettify())
        print("-" * 80)


def lxml_trace(data, html=True, **kwargs):
    """Print out the lxml events that occur during parsing.

    This lets you see how lxml parses a document when no Beautiful
    Soup code is running. You can use this to determine whether
    an lxml-specific problem is in Bisque's lxml tree builders
    or in lxml itself.

    :param data: Some markup.
    :param html: If True, markup will be parsed with lxml's HTML parser.
       if False, lxml's XML parser will be used.
    """
    from lxml import etree

    recover = kwargs.pop("recover", True)
    if isinstance(data, str):
        data = data.encode("utf8")
    reader = BytesIO(data)
    for event, element in etree.iterparse(reader, html=html, recover=recover, **kwargs):
        print("%s, %4s, %s" % (event, element.tag, element.text))


class AnnouncingParser(HTMLParser):
    """Subclass of HTMLParser that announces parse events, without doing
    anything else.

    You can use this to get a picture of how html.parser sees a given
    document. The easiest way to do this is to call `htmlparser_trace`.
    """

    def _p(self, s):
        print(s)

    def handle_starttag(self, name, attrs):
        self._p(f"{name} START")

    def handle_endtag(self, name):
        self._p(f"{name} END")

    def handle_data(self, data):
        self._p(f"{data} DATA")

    def handle_charref(self, name):
        self._p(f"{name} CHARREF")

    def handle_entityref(self, name):
        self._p(f"{name} ENTITYREF")

    def handle_comment(self, data):
        self._p(f"{data} COMMENT")

    def handle_decl(self, data):
        self._p(f"{data} DECL")

    def unknown_decl(self, data):
        self._p(f"{data} UNKNOWN-DECL")

    def handle_pi(self, data):
        self._p(f"{data} PI")


def htmlparser_trace(data):
    """Print out the HTMLParser events that occur during parsing.

    This lets you see how HTMLParser parses a document when no
    Bisque code is running.

    :param data: Some markup.
    """
    parser = AnnouncingParser()
    parser.feed(data)


def rword(length=5):
    "Generate a random word-like string."
    s = ""
    for i in range(length):
        if i % 2 == 0:
            t = _consonants
        else:
            t = _vowels
        s += random.choice(t)
    return s


def rsentence(length=4):
    "Generate a random sentence-like string."
    return " ".join(rword(random.randint(4, 9)) for i in range(length))


def rdoc(num_elements=1000):
    """Randomly generate an invalid HTML document."""
    tag_names = ["p", "div", "span", "i", "b", "script", "table"]
    elements = []
    for i in range(num_elements):
        choice = random.randint(0, 3)
        if choice == 0:
            # New tag.
            tag_name = random.choice(tag_names)
            elements.append("<%s>" % tag_name)
        elif choice == 1:
            elements.append(rsentence(random.randint(1, 4)))
        elif choice == 2:
            # Close a tag.
            tag_name = random.choice(tag_names)
            elements.append("</%s>" % tag_name)
    return "<html>" + "\n".join(elements) + "</html>"


def benchmark_parsers(num_elements=100000):
    """Very basic head-to-head performance benchmark."""
    print("Comparative parser benchmark on Bisque %s" % __version__)
    data = rdoc(num_elements)
    print("Generated a large invalid HTML document (%d bytes)." % len(data))

    for parser in ["lxml", ["lxml", "html"], "html5lib", "html.parser"]:
        success = False
        try:
            a = time.time()
            Bisque(data, parser)
            b = time.time()
            success = True
        except Exception:
            print("%s could not parse the markup." % parser)
            traceback.print_exc()
        if success:
            print(f"Bisque+{parser} parsed the markup in {b - a:.2f}s.")

    from lxml import etree

    a = time.time()
    etree.HTML(data)
    b = time.time()
    print("Raw lxml parsed the markup in %.2fs." % (b - a))

    import html5lib

    parser = html5lib.HTMLParser()
    a = time.time()
    parser.parse(data)
    b = time.time()
    print("Raw html5lib parsed the markup in %.2fs." % (b - a))


def profile(num_elements=100000, parser="lxml"):
    """Use Python's profiler on a randomly generated document."""
    filehandle = tempfile.NamedTemporaryFile()
    filename = filehandle.name
    data = rdoc(num_elements)
    vars = dict(bisque=bisque, data=data, parser=parser)
    cProfile.runctx("bisque.Bisque(data, parser)", vars, vars, filename)
    stats = pstats.Stats(filename)
    stats.sort_stats("cumulative")
    stats.print_stats("_html5lib|bisque", 50)


def diagnose_html():
    """If this file is run as a script, standard input is diagnosed."""
    diagnose(sys.stdin.read())
