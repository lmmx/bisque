from bisque.builder.core.features import HTML, STRICT
from bisque.builder.core.html_builder import HTMLTreeBuilder
from bisque.builder.core.main import ParserRejectedMarkup
from bisque.builder.core.parser_names import HTMLPARSER
from bisque.dammit import UnicodeDammit
from bisque.models import StrTypes

from .parser import BisqueHTMLParser

__all__ = ["HTMLParserTreeBuilder"]


class HTMLParserTreeBuilder(HTMLTreeBuilder):
    """A Beautiful soup `TreeBuilder` that uses the `HTMLParser` parser,
    found in the Python standard library.
    """

    is_xml = False
    picklable = True
    NAME = HTMLPARSER
    features = [NAME, HTML, STRICT]
    # The html.parser knows which line number and position in the
    # original file is the source of an element.
    TRACKS_LINE_NUMBERS = True

    def __init__(self, parser_args=None, parser_kwargs=None, **kwargs):
        """Constructor.

        :param parser_args: Positional arguments to pass into
            the BisqueHTMLParser constructor, once it's
            invoked.
        :param parser_kwargs: Keyword arguments to pass into
            the BisqueHTMLParser constructor, once it's
            invoked.
        :param kwargs: Keyword arguments for the superclass constructor.
        """
        # Some keyword arguments will be pulled out of kwargs and placed
        # into parser_kwargs.
        extra_parser_kwargs = dict()
        for arg in ("on_duplicate_attribute",):
            if arg in kwargs:
                value = kwargs.pop(arg)
                extra_parser_kwargs[arg] = value
        super().__init__(**kwargs)
        parser_args = parser_args or []
        parser_kwargs = parser_kwargs or {}
        parser_kwargs.update(extra_parser_kwargs)
        parser_kwargs["convert_charrefs"] = False
        self.parser_args = (parser_args, parser_kwargs)

    def prepare_markup(
        self,
        markup,
        user_specified_encoding=None,
        document_declared_encoding=None,
        exclude_encodings=None,
    ):
        """Run any preliminary steps necessary to make incoming markup
        acceptable to the parser.

        :param markup: Some markup -- probably a bytestring.
        :param user_specified_encoding: The user asked to try this encoding.
        :param document_declared_encoding: The markup itself claims to be
            in this encoding.
        :param exclude_encodings: The user asked _not_ to try any of
            these encodings.

        :yield: A series of 4-tuples:
         (markup, encoding, declared encoding,
          has undergone character replacement)

         Each 4-tuple represents a strategy for converting the
         document to Unicode and parsing it. Each strategy will be tried
         in turn.
        """
        if isinstance(markup, StrTypes):
            # Parse Unicode as-is.
            yield (markup, None, None, False)
            return
        # Ask UnicodeDammit to sniff the most likely encoding.
        # This was provided by the end-user; treat it as a known
        # definite encoding per the algorithm laid out in the HTML5
        # spec.  (See the EncodingDetector class for details.)
        known_definite_encodings = [user_specified_encoding]
        # This was found in the document; treat it as a slightly lower-priority
        # user encoding.
        user_encodings = [document_declared_encoding]
        # Never used: mistake?
        # try_encodings = [user_specified_encoding, document_declared_encoding]
        dammit = UnicodeDammit(
            markup,
            known_definite_encodings=known_definite_encodings,
            user_encodings=user_encodings,
            is_html=True,
            exclude_encodings=exclude_encodings,
        )
        yield (
            dammit.markup,
            dammit.original_encoding,
            dammit.declared_html_encoding,
            dammit.contains_replacement_characters,
        )

    def feed(self, markup):
        """Run some incoming markup through some parsing process,
        populating the `Bisque` object in self.soup.
        """
        args, kwargs = self.parser_args
        parser = BisqueHTMLParser(*args, **kwargs)
        parser.soup = self.soup
        try:
            parser.feed(markup)
            parser.close()
        except AssertionError as e:
            # html.parser raises AssertionError in rare cases to
            # indicate a fatal problem with the markup, especially
            # when there's an error in the doctype declaration.
            raise ParserRejectedMarkup(e)
        parser.already_closed_empty_element = []
