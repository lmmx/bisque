import sys

from pydantic import BaseModel

__all__ = ["BaseTypeTable", "EmptyTypeTableError", "MissingClassVarError"]


class EmptyTypeTableError(TypeError):
    """Raised when the type table is empty."""

    def __init__(self, cls_name: str):
        super().__init__(f"Type table is empty: {cls_name} has no class variables set.")


class MissingClassVarError(TypeError):
    """Raised when a model doesn't have a specific classvar set."""

    def __init__(self, tabulated_type: str, cls_name: str):
        super().__init__(
            f"{tabulated_type} model has no {cls_name!r} classvar set. "
            "Hint: inherit from the `TabulatedType` mixin or set it manually.",
        )


class BaseTypeTable(BaseModel):
    """
    Provides a helper method that will populate the model that inherits from this class.
    See https://github.com/lmmx/interface-separation-example for full details.
    """

    @classmethod
    def setup(cls) -> None:
        """
        For each class variable on this type table class, get the module namespace value
        (i.e. a class in the same file as this type table class) with that name, and
        assign it as the value of the class variable. This 'sets up' the type table.

        Raise an error if there are no class variables set on the type table or there is
        no class in the module namespace with the name of a type table class variable.
        """
        cls_name = cls.__name__
        if not (cls_vars := cls.__class_vars__):
            raise EmptyTypeTableError(cls_name)
        module_namespace = vars(sys.modules[cls.__module__])
        for classvar in cls_vars:
            tabulated_type = module_namespace[classvar]
            if getattr(tabulated_type, cls_name, None) is not cls:
                raise MissingClassVarError(tabulated_type, cls_name)
            setattr(cls, classvar, tabulated_type)
        return
