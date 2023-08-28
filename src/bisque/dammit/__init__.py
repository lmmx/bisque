"""Bisque bonus library: Unicode, Dammit

This library converts a bytestream to Unicode through any means
necessary. It is heavily based on code from Mark Pilgrim's Universal
Feed Parser. It works best on XML and HTML, but it does not rewrite the
XML or HTML to reflect a new encoding; that's the tree builder's job.
"""
from .detection import EncodingDetector, UnicodeDammit, chardet_dammit
from .substitution import EntitySubstitution
