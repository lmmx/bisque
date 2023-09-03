from __future__ import annotations

__all__ = ["BasePreformattedString"]


class BasePreformattedString:
    """A NavigableString not subject to the normal formatting rules.

    This is an abstract class used for special kinds of strings such as
    comments (the Comment class) and CDATA blocks (the CData class).
    """

    def output_ready(self, formatter=None):
        """Make this string ready for output by adding any subclass-specific
            prefix or suffix.

        :param formatter: A Formatter object, or a string naming one
            of the standard formatters. The string will be passed into the
            Formatter, but only to trigger any side effects: the return
            value is ignored.

        :return: The string, with any subclass-specific prefix and
           suffix added on.
        """
        if formatter is not None:
            # this used to assign to an unused var named "ignore"
            self.format_string(self, formatter)
        return self.PREFIX + str(self) + self.SUFFIX
