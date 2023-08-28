import re

from html5lib.constants import prefixes
from html5lib.treebuilders import base as treebuilder_base

from bisque.element import Comment, Doctype, NamespacedAttribute, NavigableString

from .element_and_text import Element, TextNode

__all__ = ["TreeBuilderForHtml5lib"]


class TreeBuilderForHtml5lib(treebuilder_base.TreeBuilder):
    def __init__(
        self,
        namespaceHTMLElements,
        soup=None,
        store_line_numbers=True,
        **kwargs,
    ):
        if soup:
            self.soup = soup
        else:
            from bisque import Bisque

            # TODO: Why is the parser 'html.parser' here? To avoid an
            # infinite loop?
            self.soup = Bisque(
                "",
                "html.parser",
                store_line_numbers=store_line_numbers,
                **kwargs,
            )
        # TODO: What are **kwargs exactly? Should they be passed in
        # here in addition to/instead of being passed to the Bisque
        # constructor?
        super().__init__(namespaceHTMLElements)
        # This will be set later to an html5lib.html5parser.HTMLParser
        # object, which we can use to track the current line number.
        self.parser = None
        self.store_line_numbers = store_line_numbers

    def documentClass(self):
        self.soup.reset()
        return Element(self.soup, self.soup, None)

    def insertDoctype(self, token):
        name = token["name"]
        publicId = token["publicId"]
        systemId = token["systemId"]
        doctype = Doctype.for_name_and_ids(name, publicId, systemId)
        self.soup.object_was_parsed(doctype)

    def elementClass(self, name, namespace):
        kwargs = {}
        if self.parser and self.store_line_numbers:
            # This represents the point immediately after the end of the
            # tag. We don't know when the tag started, but we do know
            # where it ended -- the character just before this one.
            sourceline, sourcepos = self.parser.tokenizer.stream.position()
            kwargs["sourceline"] = sourceline
            kwargs["sourcepos"] = sourcepos - 1
        tag = self.soup.new_tag(name, namespace, **kwargs)
        return Element(tag, self.soup, namespace)

    def commentClass(self, data):
        return TextNode(Comment(data), self.soup)

    def fragmentClass(self):
        from bisque import Bisque

        # TODO: Why is the parser 'html.parser' here? To avoid an
        # infinite loop?
        self.soup = Bisque("", "html.parser")
        self.soup.name = "[document_fragment]"
        return Element(self.soup, self.soup, None)

    def appendChild(self, node):
        # XXX This code is not covered by the BS4 tests.
        self.soup.append(node.element)

    def getDocument(self):
        return self.soup

    def getFragment(self):
        return treebuilder_base.TreeBuilder.getFragment(self).element

    def testSerializer(self, element):
        from bisque import Bisque

        rv = []
        doctype_re = re.compile(
            r'^(.*?)(?: PUBLIC "(.*?)"(?: "(.*?)")?| SYSTEM "(.*?)")?$',
        )

        def serializeElement(element, indent=0):
            if isinstance(element, Bisque):
                pass
            if isinstance(element, Doctype):
                m = doctype_re.match(element)
                if m:
                    name = m.group(1)
                    if m.lastindex > 1:
                        publicId = m.group(2) or ""
                        systemId = m.group(3) or m.group(4) or ""
                        rv.append(
                            """|%s<!DOCTYPE %s "%s" "%s">"""
                            % (" " * indent, name, publicId, systemId),
                        )
                    else:
                        rv.append("|{}<!DOCTYPE {}>".format(" " * indent, name))
                else:
                    rv.append("|{}<!DOCTYPE >".format(" " * indent))
            elif isinstance(element, Comment):
                rv.append("|{}<!-- {} -->".format(" " * indent, element))
            elif isinstance(element, NavigableString):
                rv.append('|{}"{}"'.format(" " * indent, element))
            else:
                if element.namespace:
                    name = f"{prefixes[element.namespace]} {element.name}"
                else:
                    name = element.name
                rv.append("|{}<{}>".format(" " * indent, name))
                if element.attrs:
                    attributes = []
                    for name, value in list(element.attrs.items()):
                        if isinstance(name, NamespacedAttribute):
                            name = f"{prefixes[name.namespace]} {name.name}"
                        if isinstance(value, list):
                            value = " ".join(value)
                        attributes.append((name, value))
                    for name, value in sorted(attributes):
                        rv.append('|{}{}="{}"'.format(" " * (indent + 2), name, value))
                indent += 2
                for child in element.children:
                    serializeElement(child, indent)

        serializeElement(element, 0)
        return "\n".join(rv)
