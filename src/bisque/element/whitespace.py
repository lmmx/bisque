import re

__all__ = ["nonwhitespace_re", "whitespace_re"]

nonwhitespace_re = re.compile(r"\S+")

# NOTE: This isn't used as of 4.7.0. I'm leaving it for a little bit on
# the off chance someone imported it for their own use.
whitespace_re = re.compile(r"\s+")
