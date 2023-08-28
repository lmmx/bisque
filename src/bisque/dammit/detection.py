import codecs
import logging
import re

from .dependency_resolution import chardet_module
from .encodings import encoding_res

__all__ = ["chardet_dammit", "UnicodeDammit", "EncodingDetector", "UnicodeDammit"]


def chardet_dammit(s):
    if chardet_module is None or isinstance(s, str):
        return None
    else:
        return chardet_module.detect(s)["encoding"]


class EncodingDetector:
    """Suggests a number of possible encodings for a bytestring.

    Order of precedence:

    1. Encodings you specifically tell EncodingDetector to try first
    (the known_definite_encodings argument to the constructor).

    2. An encoding determined by sniffing the document's byte-order mark.

    3. Encodings you specifically tell EncodingDetector to try if
    byte-order mark sniffing fails (the user_encodings argument to the
    constructor).

    4. An encoding declared within the bytestring itself, either in an
    XML declaration (if the bytestring is to be interpreted as an XML
    document), or in a <meta> tag (if the bytestring is to be
    interpreted as an HTML document.)

    5. An encoding detected through textual analysis by chardet,
    cchardet, or a similar external library.

    4. UTF-8.

    5. Windows-1252.

    """

    def __init__(
        self,
        markup,
        known_definite_encodings=None,
        is_html=False,
        exclude_encodings=None,
        user_encodings=None,
        override_encodings=None,
    ):
        """Constructor.

        :param markup: Some markup in an unknown encoding.

        :param known_definite_encodings: When determining the encoding
            of `markup`, these encodings will be tried first, in
            order. In HTML terms, this corresponds to the "known
            definite encoding" step defined here:
            https://html.spec.whatwg.org/multipage/parsing.html#parsing-with-a-known-character-encoding

        :param user_encodings: These encodings will be tried after the
            `known_definite_encodings` have been tried and failed, and
            after an attempt to sniff the encoding by looking at a
            byte order mark has failed. In HTML terms, this
            corresponds to the step "user has explicitly instructed
            the user agent to override the document's character
            encoding", defined here:
            https://html.spec.whatwg.org/multipage/parsing.html#determining-the-character-encoding

        :param override_encodings: A deprecated alias for
            known_definite_encodings. Any encodings here will be tried
            immediately after the encodings in
            known_definite_encodings.

        :param is_html: If True, this markup is considered to be
            HTML. Otherwise it's assumed to be XML.

        :param exclude_encodings: These encodings will not be tried,
            even if they otherwise would be.

        """
        self.known_definite_encodings = list(known_definite_encodings or [])
        if override_encodings:
            self.known_definite_encodings += override_encodings
        self.user_encodings = user_encodings or []
        exclude_encodings = exclude_encodings or []
        self.exclude_encodings = {x.lower() for x in exclude_encodings}
        self.chardet_encoding = None
        self.is_html = is_html
        self.declared_encoding = None

        # First order of business: strip a byte-order mark.
        self.markup, self.sniffed_encoding = self.strip_byte_order_mark(markup)

    def _usable(self, encoding, tried):
        """Should we even bother to try this encoding?

        :param encoding: Name of an encoding.
        :param tried: Encodings that have already been tried. This will be modified
            as a side effect.
        """
        if encoding is not None:
            encoding = encoding.lower()
            if encoding in self.exclude_encodings:
                return False
            if encoding not in tried:
                tried.add(encoding)
                return True
        return False

    @property
    def encodings(self):
        """Yield a number of encodings that might work for this markup.

        :yield: A sequence of strings.
        """
        tried = set()
        # First, try the known definite encodings
        for e in self.known_definite_encodings:
            if self._usable(e, tried):
                yield e
        # Did the document originally start with a byte-order mark
        # that indicated its encoding?
        if self._usable(self.sniffed_encoding, tried):
            yield self.sniffed_encoding
        # Sniffing the byte-order mark did nothing; try the user
        # encodings.
        for e in self.user_encodings:
            if self._usable(e, tried):
                yield e
        # Look within the document for an XML or HTML encoding
        # declaration.
        if self.declared_encoding is None:
            self.declared_encoding = self.find_declared_encoding(
                self.markup,
                self.is_html,
            )
        if self._usable(self.declared_encoding, tried):
            yield self.declared_encoding
        # Use third-party character set detection to guess at the
        # encoding.
        if self.chardet_encoding is None:
            self.chardet_encoding = chardet_dammit(self.markup)
        if self._usable(self.chardet_encoding, tried):
            yield self.chardet_encoding
        # As a last-ditch effort, try utf-8 and windows-1252.
        for e in ("utf-8", "windows-1252"):
            if self._usable(e, tried):
                yield e

    @classmethod
    def strip_byte_order_mark(cls, data):
        """If a byte-order mark is present, strip it and return the encoding it implies.

        :param data: Some markup.
        :return: A 2-tuple (modified data, implied encoding)
        """
        encoding = None
        if isinstance(data, str):
            # Unicode data cannot have a byte-order mark.
            return data, encoding
        if (len(data) >= 4) and (data[:2] == b"\xfe\xff") and (data[2:4] != "\x00\x00"):
            encoding = "utf-16be"
            data = data[2:]
        elif (
            (len(data) >= 4) and (data[:2] == b"\xff\xfe") and (data[2:4] != "\x00\x00")
        ):
            encoding = "utf-16le"
            data = data[2:]
        elif data[:3] == b"\xef\xbb\xbf":
            encoding = "utf-8"
            data = data[3:]
        elif data[:4] == b"\x00\x00\xfe\xff":
            encoding = "utf-32be"
            data = data[4:]
        elif data[:4] == b"\xff\xfe\x00\x00":
            encoding = "utf-32le"
            data = data[4:]
        return data, encoding

    @classmethod
    def find_declared_encoding(
        cls,
        markup,
        is_html=False,
        search_entire_document=False,
    ):
        """Given a document, tries to find its declared encoding.

        An XML encoding is declared at the beginning of the document.

        An HTML encoding is declared in a <meta> tag, hopefully near the
        beginning of the document.

        :param markup: Some markup.
        :param is_html: If True, this markup is considered to be HTML. Otherwise
            it's assumed to be XML.
        :param search_entire_document: Since an encoding is supposed to declared near the beginning
            of the document, most of the time it's only necessary to search a few kilobytes of data.
            Set this to True to force this method to search the entire document.
        """
        if search_entire_document:
            xml_endpos = html_endpos = len(markup)
        else:
            xml_endpos = 1024
            html_endpos = max(2048, int(len(markup) * 0.05))
        if isinstance(markup, bytes):
            res = encoding_res[bytes]
        else:
            res = encoding_res[str]
        xml_re = res["xml"]
        html_re = res["html"]
        declared_encoding = None
        declared_encoding_match = xml_re.search(markup, endpos=xml_endpos)
        if not declared_encoding_match and is_html:
            declared_encoding_match = html_re.search(markup, endpos=html_endpos)
        if declared_encoding_match is not None:
            declared_encoding = declared_encoding_match.groups()[0]
        if declared_encoding:
            if isinstance(declared_encoding, bytes):
                declared_encoding = declared_encoding.decode("ascii", "replace")
            return declared_encoding.lower()
        return None


class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = {"macintosh": "mac-roman", "x-sjis": "shift-jis"}
    ENCODINGS_WITH_SMART_QUOTES = ["windows-1252", "iso-8859-1", "iso-8859-2"]

    def __init__(
        self,
        markup,
        known_definite_encodings=[],
        smart_quotes_to=None,
        is_html=False,
        exclude_encodings=[],
        user_encodings=None,
        override_encodings=None,
    ):
        """Constructor.

        :param markup: A bytestring representing markup in an unknown encoding.

        :param known_definite_encodings: When determining the encoding
            of `markup`, these encodings will be tried first, in
            order. In HTML terms, this corresponds to the "known
            definite encoding" step defined here:
            https://html.spec.whatwg.org/multipage/parsing.html#parsing-with-a-known-character-encoding

        :param user_encodings: These encodings will be tried after the
            `known_definite_encodings` have been tried and failed, and
            after an attempt to sniff the encoding by looking at a
            byte order mark has failed. In HTML terms, this
            corresponds to the step "user has explicitly instructed
            the user agent to override the document's character
            encoding", defined here:
            https://html.spec.whatwg.org/multipage/parsing.html#determining-the-character-encoding

        :param override_encodings: A deprecated alias for
            known_definite_encodings. Any encodings here will be tried
            immediately after the encodings in
            known_definite_encodings.

        :param smart_quotes_to: By default, Microsoft smart quotes will, like all other characters, be converted
           to Unicode characters. Setting this to 'ascii' will convert them to ASCII quotes instead.
           Setting it to 'xml' will convert them to XML entity references, and setting it to 'html'
           will convert them to HTML entity references.
        :param is_html: If True, this markup is considered to be HTML. Otherwise
            it's assumed to be XML.
        :param exclude_encodings: These encodings will not be considered, even
            if the sniffing code thinks they might make sense.

        """
        self.smart_quotes_to = smart_quotes_to
        self.tried_encodings = []
        self.contains_replacement_characters = False
        self.is_html = is_html
        self.log = logging.getLogger(__name__)
        self.detector = EncodingDetector(
            markup,
            known_definite_encodings,
            is_html,
            exclude_encodings,
            user_encodings,
            override_encodings,
        )
        # Short-circuit if the data is in Unicode to begin with.
        if isinstance(markup, str) or markup == "":
            self.markup = markup
            self.unicode_markup = str(markup)
            self.original_encoding = None
            return
        # The encoding detector may have stripped a byte-order mark.
        # Use the stripped markup from this point on.
        self.markup = self.detector.markup
        u = None
        for encoding in self.detector.encodings:
            markup = self.detector.markup
            u = self._convert_from(encoding)
            if u is not None:
                break
        if not u:
            # None of the encodings worked. As an absolute last resort,
            # try them again with character replacement.
            for encoding in self.detector.encodings:
                if encoding != "ascii":
                    u = self._convert_from(encoding, "replace")
                if u is not None:
                    self.log.warning(
                        "Some characters could not be decoded, and were "
                        "replaced with REPLACEMENT CHARACTER.",
                    )
                    self.contains_replacement_characters = True
                    break
        # If none of that worked, we could at this point force it to
        # ASCII, but that would destroy so much data that I think
        # giving up is better.
        self.unicode_markup = u
        if not u:
            self.original_encoding = None

    def _sub_ms_char(self, match):
        """Changes a MS smart quote character to an XML or HTML
        entity, or an ASCII character."""
        orig = match.group(1)
        if self.smart_quotes_to == "ascii":
            sub = self.MS_CHARS_TO_ASCII.get(orig).encode()
        else:
            sub = self.MS_CHARS.get(orig)
            if isinstance(sub, tuple):
                if self.smart_quotes_to == "xml":
                    sub = b"&#x" + sub[1].encode() + b";"
                else:
                    sub = b"&" + sub[0].encode() + b";"
            else:
                sub = sub.encode()
        return sub

    def _convert_from(self, proposed, errors="strict"):
        """Attempt to convert the markup to the proposed encoding.

        :param proposed: The name of a character encoding.
        """
        proposed = self.find_codec(proposed)
        if not proposed or (proposed, errors) in self.tried_encodings:
            return None
        self.tried_encodings.append((proposed, errors))
        markup = self.markup
        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if (
            self.smart_quotes_to is not None
            and proposed in self.ENCODINGS_WITH_SMART_QUOTES
        ):
            smart_quotes_re = b"([\x80-\x9f])"
            smart_quotes_compiled = re.compile(smart_quotes_re)
            markup = smart_quotes_compiled.sub(self._sub_ms_char, markup)
        try:
            # print(f"Trying to convert document to {proposed} ({errors=})")
            self.markup = self._to_unicode(markup, proposed, errors)
            self.original_encoding = proposed
        except Exception:
            return None
        # print(f"Correct encoding: {proposed}")
        return self.markup

    def _to_unicode(self, data, encoding, errors="strict"):
        """Given a string and its encoding, decodes the string into Unicode.

        :param encoding: The name of an encoding.
        """
        return str(data, encoding, errors)

    @property
    def declared_html_encoding(self):
        """If the markup is an HTML document, returns the encoding declared _within_
        the document.
        """
        return self.detector.declared_encoding if self.is_html else None

    def find_codec(self, charset):
        """Convert the name of a character set to a codec name.

        :param charset: The name of a character set.
        :return: The name of a codec.
        """
        value = (
            self._codec(self.CHARSET_ALIASES.get(charset, charset))
            or (charset and self._codec(charset.replace("-", "")))
            or (charset and self._codec(charset.replace("-", "_")))
            or (charset and charset.lower())
            or charset
        )
        return value.lower() if value else None

    def _codec(self, charset):
        if not charset:
            return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    # A partial mapping of ISO-Latin-1 to HTML entities/XML numeric entities.
    MS_CHARS = {
        b"\x80": ("euro", "20AC"),
        b"\x81": " ",
        b"\x82": ("sbquo", "201A"),
        b"\x83": ("fnof", "192"),
        b"\x84": ("bdquo", "201E"),
        b"\x85": ("hellip", "2026"),
        b"\x86": ("dagger", "2020"),
        b"\x87": ("Dagger", "2021"),
        b"\x88": ("circ", "2C6"),
        b"\x89": ("permil", "2030"),
        b"\x8A": ("Scaron", "160"),
        b"\x8B": ("lsaquo", "2039"),
        b"\x8C": ("OElig", "152"),
        b"\x8D": "?",
        b"\x8E": ("#x17D", "17D"),
        b"\x8F": "?",
        b"\x90": "?",
        b"\x91": ("lsquo", "2018"),
        b"\x92": ("rsquo", "2019"),
        b"\x93": ("ldquo", "201C"),
        b"\x94": ("rdquo", "201D"),
        b"\x95": ("bull", "2022"),
        b"\x96": ("ndash", "2013"),
        b"\x97": ("mdash", "2014"),
        b"\x98": ("tilde", "2DC"),
        b"\x99": ("trade", "2122"),
        b"\x9a": ("scaron", "161"),
        b"\x9b": ("rsaquo", "203A"),
        b"\x9c": ("oelig", "153"),
        b"\x9d": "?",
        b"\x9e": ("#x17E", "17E"),
        b"\x9f": ("Yuml", ""),
    }

    # A parochial partial mapping of ISO-Latin-1 to ASCII. Contains
    # horrors like stripping diacritical marks to turn á into a, but also
    # contains non-horrors like turning “ into ".
    MS_CHARS_TO_ASCII = {
        b"\x80": "EUR",
        b"\x81": " ",
        b"\x82": ",",
        b"\x83": "f",
        b"\x84": ",,",
        b"\x85": "...",
        b"\x86": "+",
        b"\x87": "++",
        b"\x88": "^",
        b"\x89": "%",
        b"\x8a": "S",
        b"\x8b": "<",
        b"\x8c": "OE",
        b"\x8d": "?",
        b"\x8e": "Z",
        b"\x8f": "?",
        b"\x90": "?",
        b"\x91": "'",
        b"\x92": "'",
        b"\x93": '"',
        b"\x94": '"',
        b"\x95": "*",
        b"\x96": "-",
        b"\x97": "--",
        b"\x98": "~",
        b"\x99": "(TM)",
        b"\x9a": "s",
        b"\x9b": ">",
        b"\x9c": "oe",
        b"\x9d": "?",
        b"\x9e": "z",
        b"\x9f": "Y",
        b"\xa0": " ",
        b"\xa1": "!",
        b"\xa2": "c",
        b"\xa3": "GBP",
        b"\xa4": "$",  # This approximation is especially parochial--this is the
        # generic currency symbol.
        b"\xa5": "YEN",
        b"\xa6": "|",
        b"\xa7": "S",
        b"\xa8": "..",
        b"\xa9": "",
        b"\xaa": "(th)",
        b"\xab": "<<",
        b"\xac": "!",
        b"\xad": " ",
        b"\xae": "(R)",
        b"\xaf": "-",
        b"\xb0": "o",
        b"\xb1": "+-",
        b"\xb2": "2",
        b"\xb3": "3",
        b"\xb4": ("'", "acute"),
        b"\xb5": "u",
        b"\xb6": "P",
        b"\xb7": "*",
        b"\xb8": ",",
        b"\xb9": "1",
        b"\xba": "(th)",
        b"\xbb": ">>",
        b"\xbc": "1/4",
        b"\xbd": "1/2",
        b"\xbe": "3/4",
        b"\xbf": "?",
        b"\xc0": "A",
        b"\xc1": "A",
        b"\xc2": "A",
        b"\xc3": "A",
        b"\xc4": "A",
        b"\xc5": "A",
        b"\xc6": "AE",
        b"\xc7": "C",
        b"\xc8": "E",
        b"\xc9": "E",
        b"\xca": "E",
        b"\xcb": "E",
        b"\xcc": "I",
        b"\xcd": "I",
        b"\xce": "I",
        b"\xcf": "I",
        b"\xd0": "D",
        b"\xd1": "N",
        b"\xd2": "O",
        b"\xd3": "O",
        b"\xd4": "O",
        b"\xd5": "O",
        b"\xd6": "O",
        b"\xd7": "*",
        b"\xd8": "O",
        b"\xd9": "U",
        b"\xda": "U",
        b"\xdb": "U",
        b"\xdc": "U",
        b"\xdd": "Y",
        b"\xde": "b",
        b"\xdf": "B",
        b"\xe0": "a",
        b"\xe1": "a",
        b"\xe2": "a",
        b"\xe3": "a",
        b"\xe4": "a",
        b"\xe5": "a",
        b"\xe6": "ae",
        b"\xe7": "c",
        b"\xe8": "e",
        b"\xe9": "e",
        b"\xea": "e",
        b"\xeb": "e",
        b"\xec": "i",
        b"\xed": "i",
        b"\xee": "i",
        b"\xef": "i",
        b"\xf0": "o",
        b"\xf1": "n",
        b"\xf2": "o",
        b"\xf3": "o",
        b"\xf4": "o",
        b"\xf5": "o",
        b"\xf6": "o",
        b"\xf7": "/",
        b"\xf8": "o",
        b"\xf9": "u",
        b"\xfa": "u",
        b"\xfb": "u",
        b"\xfc": "u",
        b"\xfd": "y",
        b"\xfe": "b",
        b"\xff": "y",
    }

    # A map used when removing rogue Windows-1252/ISO-8859-1 characters in otherwise
    # UTF-8 documents.
    #
    # Note that \x81, \x8d, \x8f, \x90, and \x9d are undefined in Windows-1252.
    WINDOWS_1252_TO_UTF8 = {
        0x80: b"\xe2\x82\xac",  # €
        0x82: b"\xe2\x80\x9a",  # ‚
        0x83: b"\xc6\x92",  # ƒ
        0x84: b"\xe2\x80\x9e",  # „
        0x85: b"\xe2\x80\xa6",  # …
        0x86: b"\xe2\x80\xa0",  # †
        0x87: b"\xe2\x80\xa1",  # ‡
        0x88: b"\xcb\x86",  # ˆ
        0x89: b"\xe2\x80\xb0",  # ‰
        0x8A: b"\xc5\xa0",  # Š
        0x8B: b"\xe2\x80\xb9",  # ‹
        0x8C: b"\xc5\x92",  # Œ
        0x8E: b"\xc5\xbd",  # Ž
        0x91: b"\xe2\x80\x98",  # ‘
        0x92: b"\xe2\x80\x99",  # ’
        0x93: b"\xe2\x80\x9c",  # “
        0x94: b"\xe2\x80\x9d",  # ”
        0x95: b"\xe2\x80\xa2",  # •
        0x96: b"\xe2\x80\x93",  # –
        0x97: b"\xe2\x80\x94",  # —
        0x98: b"\xcb\x9c",  # ˜
        0x99: b"\xe2\x84\xa2",  # ™
        0x9A: b"\xc5\xa1",  # š
        0x9B: b"\xe2\x80\xba",  # ›
        0x9C: b"\xc5\x93",  # œ
        0x9E: b"\xc5\xbe",  # ž
        0x9F: b"\xc5\xb8",  # Ÿ
        0xA0: b"\xc2\xa0",  #
        0xA1: b"\xc2\xa1",  # ¡
        0xA2: b"\xc2\xa2",  # ¢
        0xA3: b"\xc2\xa3",  # £
        0xA4: b"\xc2\xa4",  # ¤
        0xA5: b"\xc2\xa5",  # ¥
        0xA6: b"\xc2\xa6",  # ¦
        0xA7: b"\xc2\xa7",  # §
        0xA8: b"\xc2\xa8",  # ¨
        0xA9: b"\xc2\xa9",  # ©
        0xAA: b"\xc2\xaa",  # ª
        0xAB: b"\xc2\xab",  # «
        0xAC: b"\xc2\xac",  # ¬
        0xAD: b"\xc2\xad",  # ­
        0xAE: b"\xc2\xae",  # ®
        0xAF: b"\xc2\xaf",  # ¯
        0xB0: b"\xc2\xb0",  # °
        0xB1: b"\xc2\xb1",  # ±
        0xB2: b"\xc2\xb2",  # ²
        0xB3: b"\xc2\xb3",  # ³
        0xB4: b"\xc2\xb4",  # ´
        0xB5: b"\xc2\xb5",  # µ
        0xB6: b"\xc2\xb6",  # ¶
        0xB7: b"\xc2\xb7",  # ·
        0xB8: b"\xc2\xb8",  # ¸
        0xB9: b"\xc2\xb9",  # ¹
        0xBA: b"\xc2\xba",  # º
        0xBB: b"\xc2\xbb",  # »
        0xBC: b"\xc2\xbc",  # ¼
        0xBD: b"\xc2\xbd",  # ½
        0xBE: b"\xc2\xbe",  # ¾
        0xBF: b"\xc2\xbf",  # ¿
        0xC0: b"\xc3\x80",  # À
        0xC1: b"\xc3\x81",  # Á
        0xC2: b"\xc3\x82",  # Â
        0xC3: b"\xc3\x83",  # Ã
        0xC4: b"\xc3\x84",  # Ä
        0xC5: b"\xc3\x85",  # Å
        0xC6: b"\xc3\x86",  # Æ
        0xC7: b"\xc3\x87",  # Ç
        0xC8: b"\xc3\x88",  # È
        0xC9: b"\xc3\x89",  # É
        0xCA: b"\xc3\x8a",  # Ê
        0xCB: b"\xc3\x8b",  # Ë
        0xCC: b"\xc3\x8c",  # Ì
        0xCD: b"\xc3\x8d",  # Í
        0xCE: b"\xc3\x8e",  # Î
        0xCF: b"\xc3\x8f",  # Ï
        0xD0: b"\xc3\x90",  # Ð
        0xD1: b"\xc3\x91",  # Ñ
        0xD2: b"\xc3\x92",  # Ò
        0xD3: b"\xc3\x93",  # Ó
        0xD4: b"\xc3\x94",  # Ô
        0xD5: b"\xc3\x95",  # Õ
        0xD6: b"\xc3\x96",  # Ö
        0xD7: b"\xc3\x97",  # ×
        0xD8: b"\xc3\x98",  # Ø
        0xD9: b"\xc3\x99",  # Ù
        0xDA: b"\xc3\x9a",  # Ú
        0xDB: b"\xc3\x9b",  # Û
        0xDC: b"\xc3\x9c",  # Ü
        0xDD: b"\xc3\x9d",  # Ý
        0xDE: b"\xc3\x9e",  # Þ
        0xDF: b"\xc3\x9f",  # ß
        0xE0: b"\xc3\xa0",  # à
        0xE1: b"\xa1",  # á
        0xE2: b"\xc3\xa2",  # â
        0xE3: b"\xc3\xa3",  # ã
        0xE4: b"\xc3\xa4",  # ä
        0xE5: b"\xc3\xa5",  # å
        0xE6: b"\xc3\xa6",  # æ
        0xE7: b"\xc3\xa7",  # ç
        0xE8: b"\xc3\xa8",  # è
        0xE9: b"\xc3\xa9",  # é
        0xEA: b"\xc3\xaa",  # ê
        0xEB: b"\xc3\xab",  # ë
        0xEC: b"\xc3\xac",  # ì
        0xED: b"\xc3\xad",  # í
        0xEE: b"\xc3\xae",  # î
        0xEF: b"\xc3\xaf",  # ï
        0xF0: b"\xc3\xb0",  # ð
        0xF1: b"\xc3\xb1",  # ñ
        0xF2: b"\xc3\xb2",  # ò
        0xF3: b"\xc3\xb3",  # ó
        0xF4: b"\xc3\xb4",  # ô
        0xF5: b"\xc3\xb5",  # õ
        0xF6: b"\xc3\xb6",  # ö
        0xF7: b"\xc3\xb7",  # ÷
        0xF8: b"\xc3\xb8",  # ø
        0xF9: b"\xc3\xb9",  # ù
        0xFA: b"\xc3\xba",  # ú
        0xFB: b"\xc3\xbb",  # û
        0xFC: b"\xc3\xbc",  # ü
        0xFD: b"\xc3\xbd",  # ý
        0xFE: b"\xc3\xbe",  # þ
    }

    MULTIBYTE_MARKERS_AND_SIZES = [
        (0xC2, 0xDF, 2),  # 2-byte characters start with a byte C2-DF
        (0xE0, 0xEF, 3),  # 3-byte characters start with E0-EF
        (0xF0, 0xF4, 4),  # 4-byte characters start with F0-F4
    ]

    FIRST_MULTIBYTE_MARKER = MULTIBYTE_MARKERS_AND_SIZES[0][0]
    LAST_MULTIBYTE_MARKER = MULTIBYTE_MARKERS_AND_SIZES[-1][1]

    @classmethod
    def detwingle(
        cls,
        in_bytes,
        main_encoding="utf8",
        embedded_encoding="windows-1252",
    ):
        """Fix characters from one encoding embedded in some other encoding.

        Currently the only situation supported is Windows-1252 (or its
        subset ISO-8859-1), embedded in UTF-8.

        :param in_bytes: A bytestring that you suspect contains
            characters from multiple encodings. Note that this _must_
            be a bytestring. If you've already converted the document
            to Unicode, you're too late.
        :param main_encoding: The primary encoding of `in_bytes`.
        :param embedded_encoding: The encoding that was used to embed characters
            in the main document.
        :return: A bytestring in which `embedded_encoding`
          characters have been converted to their `main_encoding`
          equivalents.
        """
        if embedded_encoding.replace("_", "-").lower() not in (
            "windows-1252",
            "windows_1252",
        ):
            raise NotImplementedError(
                "Windows-1252 and ISO-8859-1 are the only currently supported "
                "embedded encodings.",
            )
        if main_encoding.lower() not in ("utf8", "utf-8"):
            raise NotImplementedError(
                "UTF-8 is the only currently supported main encoding.",
            )
        byte_chunks = []
        chunk_start = 0
        pos = 0
        while pos < len(in_bytes):
            byte = in_bytes[pos]
            if byte >= cls.FIRST_MULTIBYTE_MARKER and byte <= cls.LAST_MULTIBYTE_MARKER:
                # This is the start of a UTF-8 multibyte character. Skip
                # to the end.
                for start, end, size in cls.MULTIBYTE_MARKERS_AND_SIZES:
                    if byte >= start and byte <= end:
                        pos += size
                        break
            elif byte >= 0x80 and byte in cls.WINDOWS_1252_TO_UTF8:
                # We found a Windows-1252 character!
                # Save the string up to this point as a chunk.
                byte_chunks.append(in_bytes[chunk_start:pos])
                # Now translate the Windows-1252 character into UTF-8
                # and add it as another, one-byte chunk.
                byte_chunks.append(cls.WINDOWS_1252_TO_UTF8[byte])
                pos += 1
                chunk_start = pos
            else:
                # Go on to the next character.
                pos += 1
        if chunk_start == 0:
            # The string is unchanged.
            return in_bytes
        else:
            # Store the final chunk.
            byte_chunks.append(in_bytes[chunk_start:])
        return b"".join(byte_chunks)
