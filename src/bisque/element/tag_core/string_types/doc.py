from __future__ import annotations

__all__ = ["BaseDoctype"]


class BaseDoctype:
    """A document type declaration."""

    @classmethod
    def for_name_and_ids(cls, name, pub_id, system_id):
        """Generate an appropriate document type declaration for a given
        public ID and system ID.

        :param name: The name of the document's root element, e.g. 'html'.
        :param pub_id: The Formal Public Identifier for this document type,
            e.g. '-//W3C//DTD XHTML 1.1//EN'
        :param system_id: The system identifier for this document type,
            e.g. 'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'

        :return: A Doctype.
        """
        value = name or ""
        if pub_id is not None:
            value += ' PUBLIC "%s"' % pub_id
            if system_id is not None:
                value += ' "%s"' % system_id
        elif system_id is not None:
            value += ' SYSTEM "%s"' % system_id

        return cls.TYPE_TABLE.Doctype(value)
