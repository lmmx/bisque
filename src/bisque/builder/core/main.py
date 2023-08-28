"""
The main class `TreeBuilder` is a base for the `HTMLBuilder` which is then specified at
the parser level for the stdlib HTML parser, the HTML5lib parser, and the lxml parser.

`TreeBuilder` sets 9 methods:
- `__init__`
- `initialize_soup`
- `reset`
- `can_be_empty_element`
- `feed`
- `prepare_markup`
- `test_fragment_to_document`
- `set_up_substitutions`
- `_replace_cdata_list_attribute_values`

and 5 class variables
- `NAME`
- `ALTERNATE_NAMES`
- `features`
- `is_xml`
- `picklable`
- `empty_element_tags`
- `DEFAULT_CDATA_LIST_ATTRIBUTES`
- `DEFAULT_PRESERVE_WHITESPACE_TAGS`
- `DEFAULT_STRING_CONTAINERS`
- `USE_DEFAULT`
- `TRACKS_LINE_NUMBERS`
"""
from collections import defaultdict

from bisque.element import nonwhitespace_re

from .parser_names import INIT

__all__ = ["TreeBuilder", "ParserRejectedMarkup"]


class TreeBuilder:
    """Turn a textual document into a Bisque object tree."""

    NAME = INIT
    ALTERNATE_NAMES = []
    features = []

    is_xml = False
    picklable = False
    # A tag is considered an empty-element tag if and only if it has no contents.
    empty_element_tags = None
    # A value for these tag/attribute combinations is a space- or
    # comma-separated list of CDATA, rather than a single CDATA.
    DEFAULT_CDATA_LIST_ATTRIBUTES = defaultdict(list)
    # Whitespace should be preserved inside these tags.
    DEFAULT_PRESERVE_WHITESPACE_TAGS = set()
    # The textual contents of tags with these names should be
    # instantiated with some class other than NavigableString.
    DEFAULT_STRING_CONTAINERS = {}
    USE_DEFAULT = object()
    # Most parsers don't keep track of line numbers.
    TRACKS_LINE_NUMBERS = False

    def __init__(
        self,
        multi_valued_attributes=USE_DEFAULT,
        preserve_whitespace_tags=USE_DEFAULT,
        store_line_numbers=USE_DEFAULT,
        string_containers=USE_DEFAULT,
    ):
        """Constructor.

        :param multi_valued_attributes: If this is set to None, the
         TreeBuilder will not turn any values for attributes like
         'class' into lists. Setting this to a dictionary will
         customize this behavior; look at DEFAULT_CDATA_LIST_ATTRIBUTES
         for an example.

         Internally, these are called "CDATA list attributes", but that
         probably doesn't make sense to an end-user, so the argument name
         is `multi_valued_attributes`.

        :param preserve_whitespace_tags: A list of tags to treat
         the way <pre> tags are treated in HTML. Tags in this list
         are immune from pretty-printing; their contents will always be
         output as-is.

        :param string_containers: A dictionary mapping tag names to
        the classes that should be instantiated to contain the textual
        contents of those tags. The default is to use NavigableString
        for every tag, no matter what the name. You can override the
        default by changing DEFAULT_STRING_CONTAINERS.

        :param store_line_numbers: If the parser keeps track of the
         line numbers and positions of the original markup, that
         information will, by default, be stored in each corresponding
         `Tag` object. You can turn this off by passing
         store_line_numbers=False. If the parser you're using doesn't
         keep track of this information, then setting store_line_numbers=True
         will do nothing.
        """
        self.soup = None
        if multi_valued_attributes is self.USE_DEFAULT:
            multi_valued_attributes = self.DEFAULT_CDATA_LIST_ATTRIBUTES
        self.cdata_list_attributes = multi_valued_attributes
        if preserve_whitespace_tags is self.USE_DEFAULT:
            preserve_whitespace_tags = self.DEFAULT_PRESERVE_WHITESPACE_TAGS
        self.preserve_whitespace_tags = preserve_whitespace_tags
        if store_line_numbers == self.USE_DEFAULT:
            store_line_numbers = self.TRACKS_LINE_NUMBERS
        self.store_line_numbers = store_line_numbers
        if string_containers == self.USE_DEFAULT:
            string_containers = self.DEFAULT_STRING_CONTAINERS
        self.string_containers = string_containers

    def initialize_soup(self, soup):
        """The Bisque object has been initialized and is now
        being associated with the TreeBuilder.

        :param soup: A Bisque object.
        """
        self.soup = soup

    def reset(self):
        """Do any work necessary to reset the underlying parser
        for a new document.

        By default, this does nothing.
        """

    def can_be_empty_element(self, tag_name):
        """Might a tag with this name be an empty-element tag?

        The final markup may or may not actually present this tag as
        self-closing.

        For instance: an HTMLBuilder does not consider a <p> tag to be
        an empty-element tag (it's not in
        HTMLBuilder.empty_element_tags). This means an empty <p> tag
        will be presented as "<p></p>", not "<p/>" or "<p>".

        The default implementation has no opinion about which tags are
        empty-element tags, so a tag will be presented as an
        empty-element tag if and only if it has no children.
        "<foo></foo>" will become "<foo/>", and "<foo>bar</foo>" will
        be left alone.

        :param tag_name: The name of a markup tag.
        """
        if self.empty_element_tags is None:
            return True
        return tag_name in self.empty_element_tags

    def feed(self, markup):
        """Run some incoming markup through some parsing process,
        populating the `Bisque` object in self.soup.

        This method is not implemented in TreeBuilder; it must be
        implemented in subclasses.

        :return: None.
        """
        raise NotImplementedError()

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
            in this encoding. NOTE: This argument is not used by the
            calling code and can probably be removed.
        :param exclude_encodings: The user asked _not_ to try any of
            these encodings.

        :yield: A series of 4-tuples:
         (markup, encoding, declared encoding,
          has undergone character replacement)

         Each 4-tuple represents a strategy for converting the
         document to Unicode and parsing it. Each strategy will be tried
         in turn.

         By default, the only strategy is to parse the markup
         as-is. See `LXMLTreeBuilderForXML` and
         `HTMLParserTreeBuilder` for implementations that take into
         account the quirks of particular parsers.
        """
        yield markup, None, None, False

    def test_fragment_to_document(self, fragment):
        """Wrap an HTML fragment to make it look like a document.

        Different parsers do this differently. For instance, lxml
        introduces an empty <head> tag, and html5lib
        doesn't. Abstracting this away lets us write simple tests
        which run HTML fragments through the parser and compare the
        results against other HTML fragments.

        This method should not be used outside of tests.

        :param fragment: A string -- fragment of HTML.
        :return: A string -- a full HTML document.
        """
        return fragment

    def set_up_substitutions(self, tag):
        """Set up any substitutions that will need to be performed on
        a `Tag` when it's output as a string.

        By default, this does nothing. See `HTMLTreeBuilder` for a
        case where this is used.

        :param tag: A `Tag`
        :return: Whether or not a substitution was performed.
        """
        return False

    def _replace_cdata_list_attribute_values(self, tag_name, attrs):
        """When an attribute value is associated with a tag that can
        have multiple values for that attribute, convert the string
        value to a list of strings.

        Basically, replaces class="foo bar" with class=["foo", "bar"]

        NOTE: This method modifies its input in place.

        :param tag_name: The name of a tag.
        :param attrs: A dictionary containing the tag's attributes.
           Any appropriate attribute values will be modified in place.
        """
        if not attrs:
            return attrs
        if self.cdata_list_attributes:
            universal = self.cdata_list_attributes.get("*", [])
            tag_specific = self.cdata_list_attributes.get(tag_name.lower(), None)
            for attr in list(attrs.keys()):
                if attr in universal or (tag_specific and attr in tag_specific):
                    # We have a "class"-type attribute whose string
                    # value is a whitespace-separated list of
                    # values. Split it into a list.
                    value = attrs[attr]
                    if isinstance(value, str):
                        values = nonwhitespace_re.findall(value)
                    else:
                        # html5lib sometimes calls setAttributes twice
                        # for the same tag when rearranging the parse
                        # tree. On the second call the attribute value
                        # here is already a list.  If this happens,
                        # leave the value alone rather than trying to
                        # split it again.
                        values = value
                    attrs[attr] = values
        return attrs


class ParserRejectedMarkup(Exception):
    """An Exception to be raised when the underlying parser simply
    refuses to parse the given markup.
    """

    def __init__(self, message_or_exception):
        """Explain why the parser rejected the given markup, either
        with a textual explanation or another exception.
        """
        if isinstance(message_or_exception, Exception):
            e = message_or_exception
            message_or_exception = f"{e.__class__.__name__}: {str(e)}"
        super().__init__(message_or_exception)
