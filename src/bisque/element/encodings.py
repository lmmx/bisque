__all__ = ["DEFAULT_OUTPUT_ENCODING", "PYTHON_SPECIFIC_ENCODINGS"]

DEFAULT_OUTPUT_ENCODING = "utf-8"

# These encodings are recognized by Python (so PageElement.encode
# could theoretically support them) but XML and HTML don't recognize
# them (so they should not show up in an XML or HTML document as that
# document's encoding).
#
# If an XML document is encoded in one of these encodings, no encoding
# will be mentioned in the XML declaration. If an HTML document is
# encoded in one of these encodings, and the HTML document has a
# <meta> tag that mentions an encoding, the encoding will be given as
# the empty string.
#
# Source:
# https://docs.python.org/3/library/codecs.html#python-specific-encodings
PYTHON_SPECIFIC_ENCODINGS = {
    "idna",
    "mbcs",
    "oem",
    "palmos",
    "punycode",
    "raw_unicode_escape",
    "undefined",
    "unicode_escape",
    "raw-unicode-escape",
    "unicode-escape",
    "string-escape",
    "string_escape",
}
