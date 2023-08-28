from .main import TreeBuilder

__all__ = ["SAXTreeBuilder"]


class SAXTreeBuilder(TreeBuilder):
    """A Bisque treebuilder that listens for SAX events.

    This is not currently used for anything, but it demonstrates
    how a simple TreeBuilder would work.
    """

    def feed(self, markup):
        raise NotImplementedError()

    def close(self):
        pass

    def startElement(self, name, attrs):
        attrs = {key[1]: value for key, value in list(attrs.items())}
        # print("Start %s, %r" % (name, attrs))
        self.soup.handle_starttag(name, attrs)

    def endElement(self, name):
        # print("End %s" % name)
        self.soup.handle_endtag(name)

    def startElementNS(self, nsTuple, nodeName, attrs):
        # Throw away (ns, nodeName) for now.
        self.startElement(nodeName, attrs)

    def endElementNS(self, nsTuple, nodeName):
        # Throw away (ns, nodeName) for now.
        self.endElement(nodeName)
        # handler.endElementNS((ns, node.nodeName), node.nodeName)

    def startPrefixMapping(self, prefix, nodeValue):
        # Ignore the prefix for now.
        pass

    def endPrefixMapping(self, prefix):
        # Ignore the prefix for now.
        # handler.endPrefixMapping(prefix)
        pass

    def characters(self, content):
        self.soup.handle_data(content)

    def startDocument(self):
        pass

    def endDocument(self):
        pass
