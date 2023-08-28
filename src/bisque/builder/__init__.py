from contextlib import suppress

from ._htmlparser import HTMLParserTreeBuilder
from .core import TreeBuilder, TreeBuilderRegistry

__all__ = ["builder_registry", "register_treebuilders_from", "HTMLParserTreeBuilder"]

# The Bisque class will take feature lists from developers and use them
# to look up builders in this registry.
builder_registry = TreeBuilderRegistry()

# Builders are registered in reverse order of priority, so that custom
# builder registrations will take precedence. In general, we want lxml
# to take precedence over html5lib, because it's faster. And we only
# want to use HTMLParser as a last resort.

# Don't use dynamic namespace import for tree builders
# Instead we already added HTMLParserTreeBuilder to the __all__ list, just register it
builder_registry.register(HTMLParserTreeBuilder)

with suppress(ImportError):
    from ._html5lib import HTML5TreeBuilder

    # If they have html5lib installed.
    __all__ += ["HTML5TreeBuilder"]
    builder_registry.register(HTML5TreeBuilder)

with suppress(ImportError):
    from ._lxml import LXMLTreeBuilder, LXMLTreeBuilderForXML

    # If they have lxml installed.
    __all__ += ["LXMLTreeBuilder", "LXMLTreeBuilderForXML"]
    builder_registry.register(LXMLTreeBuilderForXML)
    builder_registry.register(LXMLTreeBuilder)
