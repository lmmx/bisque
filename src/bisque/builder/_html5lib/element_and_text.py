from html5lib.constants import namespaces
from html5lib.treebuilders import base as treebuilder_base

from bisque.element import Comment, NamespacedAttribute, NavigableString, Tag
from bisque.models import StrTypes

from .attrs import AttrList

__all__ = ["Element", "TextNode"]


class Element(treebuilder_base.Node):
    def __init__(self, element, soup, namespace):
        treebuilder_base.Node.__init__(self, element.name)
        self.element = element
        self.soup = soup
        self.namespace = namespace

    def appendChild(self, node):
        string_child = child = None
        if isinstance(node, StrTypes):
            # Some other piece of code decided to pass in a string
            # instead of creating a TextElement object to contain the
            # string.
            string_child = child = node
        elif isinstance(node, Tag):
            # Some other piece of code decided to pass in a Tag
            # instead of creating an Element object to contain the
            # Tag.
            child = node
        elif node.element.__class__ == NavigableString:
            string_child = child = node.element
            node.parent = self
        else:
            child = node.element
            node.parent = self

        if not isinstance(child, StrTypes) and child.parent is not None:
            node.element.extract()

        if (
            string_child is not None
            and self.element.contents
            and self.element.contents[-1].__class__ == NavigableString
        ):
            # We are appending a string onto another string.
            # TODO This has O(n^2) performance, for input like
            # "a</a>a</a>a</a>..."
            old_element = self.element.contents[-1]
            new_element = self.soup.new_string(old_element + string_child)
            old_element.replace_with(new_element)
            self.soup.most_recent_element = new_element
        else:
            if isinstance(node, StrTypes):
                # Create a brand new NavigableString from this string.
                child = self.soup.new_string(node)

            # Tell Bisque to act as if it parsed this element
            # immediately after the parent's last descendant. (Or
            # immediately after the parent, if it has no children.)
            if self.element.contents:
                most_recent_element = self.element._last_descendant(False)
            elif self.element.next_element is not None:
                # Something from further ahead in the parse tree is
                # being inserted into this earlier element. This is
                # very annoying because it means an expensive search
                # for the last element in the tree.
                most_recent_element = self.soup._last_descendant()
            else:
                most_recent_element = self.element

            self.soup.object_was_parsed(
                child,
                parent=self.element,
                most_recent_element=most_recent_element,
            )

    def getAttributes(self):
        if isinstance(self.element, Comment):
            return {}
        return AttrList(self.element)

    def setAttributes(self, attributes):
        if attributes is not None and len(attributes) > 0:
            # converted_attributes = [] # never used? # mistake?
            for name, value in list(attributes.items()):
                if isinstance(name, tuple):
                    new_name = NamespacedAttribute(*name)
                    del attributes[name]
                    attributes[new_name] = value

            self.soup.builder._replace_cdata_list_attribute_values(
                self.name,
                attributes,
            )
            for name, value in list(attributes.items()):
                self.element[name] = value

            # The attributes may contain variables that need substitution.
            # Call set_up_substitutions manually.
            #
            # The Tag constructor called this method when the Tag was created,
            # but we just set/changed the attributes, so call it again.
            self.soup.builder.set_up_substitutions(self.element)

    attributes = property(getAttributes, setAttributes)

    def insertText(self, data, insertBefore=None):
        text = TextNode(self.soup.new_string(data), self.soup)
        if insertBefore:
            self.insertBefore(text, insertBefore)
        else:
            self.appendChild(text)

    def insertBefore(self, node, refNode):
        index = self.element.index(refNode.element)
        if (
            node.element.__class__ == NavigableString
            and self.element.contents
            and self.element.contents[index - 1].__class__ == NavigableString
        ):
            # (See comments in appendChild)
            old_node = self.element.contents[index - 1]
            new_str = self.soup.new_string(old_node + node.element)
            old_node.replace_with(new_str)
        else:
            self.element.insert(index, node.element)
            node.parent = self

    def removeChild(self, node):
        node.element.extract()

    def reparentChildren(self, new_parent):
        """Move all of this tag's children into another tag."""
        # print("MOVE", self.element.contents)
        # print("FROM", self.element)
        # print("TO", new_parent.element)

        element = self.element
        new_parent_element = new_parent.element
        # Determine what this tag's next_element will be once all the children
        # are removed.
        final_next_element = element.next_sibling

        new_parents_last_descendant = new_parent_element._last_descendant(False, False)
        if len(new_parent_element.contents) > 0:
            # The new parent already contains children. We will be
            # appending this tag's children to the end.
            new_parents_last_child = new_parent_element.contents[-1]
            new_parents_last_descendant_next_element = (
                new_parents_last_descendant.next_element
            )
        else:
            # The new parent contains no children.
            new_parents_last_child = None
            new_parents_last_descendant_next_element = new_parent_element.next_element

        to_append = element.contents
        if len(to_append) > 0:
            # Set the first child's previous_element and previous_sibling
            # to elements within the new parent
            first_child = to_append[0]
            if new_parents_last_descendant is not None:
                first_child.previous_element = new_parents_last_descendant
            else:
                first_child.previous_element = new_parent_element
            first_child.previous_sibling = new_parents_last_child
            if new_parents_last_descendant is not None:
                new_parents_last_descendant.next_element = first_child
            else:
                new_parent_element.next_element = first_child
            if new_parents_last_child is not None:
                new_parents_last_child.next_sibling = first_child

            # Find the very last element being moved. It is now the
            # parent's last descendant. It has no .next_sibling and
            # its .next_element is whatever the previous last
            # descendant had.
            last_childs_last_descendant = to_append[-1]._last_descendant(False, True)

            last_childs_last_descendant.next_element = (
                new_parents_last_descendant_next_element
            )
            if new_parents_last_descendant_next_element is not None:
                # TODO: This code has no test coverage and I'm not sure
                # how to get html5lib to go through this path, but it's
                # just the other side of the previous line.
                new_parents_last_descendant_next_element.previous_element = (
                    last_childs_last_descendant
                )
            last_childs_last_descendant.next_sibling = None

        for child in to_append:
            child.parent = new_parent_element
            new_parent_element.contents.append(child)

        # Now that this element has no children, change its .next_element.
        element.contents = []
        element.next_element = final_next_element

        # print("DONE WITH MOVE")
        # print("FROM", self.element)
        # print("TO", new_parent_element)

    def cloneNode(self):
        tag = self.soup.new_tag(self.element.name, self.namespace)
        node = Element(tag, self.soup, self.namespace)
        for key, value in self.attributes:
            node.attributes[key] = value
        return node

    def hasContent(self):
        return self.element.contents

    def getNameTuple(self):
        if self.namespace is None:
            return namespaces["html"], self.name
        else:
            return self.namespace, self.name

    nameTuple = property(getNameTuple)


class TextNode(Element):
    def __init__(self, element, soup):
        treebuilder_base.Node.__init__(self, None)
        self.element = element
        self.soup = soup

    def cloneNode(self):
        raise NotImplementedError
