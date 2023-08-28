"""
Build bytestring and Unicode versions of regular expressions for finding
a declared encoding inside an XML or HTML document.
"""
import re

__all__ = ["encoding_res"]

xml_encoding = "^\\s*<\\?.*encoding=['\"](.*?)['\"].*\\?>"
html_meta = "<\\s*meta[^>]+charset\\s*=\\s*[\"']?([^>]*?)[ /;'\">]"
encoding_res = {
    bytes: {
        "html": re.compile(html_meta.encode("ascii"), re.I),
        "xml": re.compile(xml_encoding.encode("ascii"), re.I),
    },
    str: {
        "html": re.compile(html_meta, re.I),
        "xml": re.compile(xml_encoding, re.I),
    },
}
