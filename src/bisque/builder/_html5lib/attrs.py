from bisque.element import nonwhitespace_re

__all__ = ["AttrList"]


class AttrList:
    def __init__(self, element):
        self.element = element
        self.attrs = dict(self.element.attrs)

    def __iter__(self):
        return list(self.attrs.items()).__iter__()

    def __setitem__(self, name, value):
        # If this attribute is a multi-valued attribute for this element,
        # turn its value into a list.
        list_attr = self.element.cdata_list_attributes or {}
        if name in list_attr.get("*", []) or (
            self.element.name in list_attr
            and name in list_attr.get(self.element.name, [])
        ):
            # A node that is being cloned may have already undergone
            # this procedure.
            if not isinstance(value, list):
                value = nonwhitespace_re.findall(value)
        self.element[name] = value

    def items(self):
        return list(self.attrs.items())

    def keys(self):
        return list(self.attrs.keys())

    def __len__(self):
        return len(self.attrs)

    def __getitem__(self, name):
        return self.attrs[name]

    def __contains__(self, name):
        return name in list(self.attrs.keys())
