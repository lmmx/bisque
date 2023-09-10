from typing import Iterator  # , TypeVar

from pydantic import BaseModel, RootModel

__all__ = [
    "Entity",
    "RootEntity",
    "RootElement",
    "Element",
    "StrMixIn",
    "StrTypes",
    "StrRoot",
    "StrRecord",
]


class Entity(BaseModel):
    """
    Any of the string types, a PageElement, Tag, or Bisque itself.
    Not used as the base model for type tables.
    """


class Element(Entity):
    """
    Base model for PageElement, Tag, and Bisque itself.
    """


class RootEntity(RootModel):
    """
    Any of the root string types. Ideally this could be merged into entity but BaseModel
    and RootModel are not compatible (?).
    """


class RootElement(RootEntity):
    """
    Base model for ?
    """


# Perhaps possible to bind to PageElement once I also extract the pre-setup type table into 1 place?
# Element = TypeVar("ElementModel", bound=ElementMixIn)


class StrMixIn:
    """
    Base for a string-like class that can be compared, hashed, and indexed.
    """

    def __eq__(self, cmp) -> str:
        return self.__str__() == cmp

    def __hash__(self) -> int:
        return hash(self.__str__())

    def __getitem__(self, index) -> str:
        return self.__str__()[index]

    def __len__(self) -> int:
        return len(self.__str__())

    def __lt__(self, cmp) -> bool:
        return self.__str__() < cmp

    def __gt__(self, cmp) -> bool:
        return self.__str__() > cmp

    def __add__(self, cmp) -> str:
        return self.__str__() + (cmp if isinstance(cmp, str) else cmp.__str__())

    def __iter__(self) -> Iterator[str]:
        return iter(self.__str__())


StrTypes = (str, StrMixIn)  # to replace in `isinstance(str)` checks


class StrRoot(StrMixIn, RootEntity):
    """
    A very string-like single field model that can be compared, hashed, and indexed.
    By default its `__str__` representation is the value of its field.
    """

    root: str

    def __str__(self) -> str:
        return self.root


class StrRecord(StrMixIn, Entity):
    """
    A fairly string-like model that can be compared, hashed, and indexed.
    By default its `__str__` representation is the value of its first field.

    Uses the value of the first field on the deepest string-like model in the class MRO.
    """

    def __str__(self) -> str:
        str_base_model = next(
            sup
            for sup in reversed(self.__class__.mro())
            if issubclass(sup, BaseModel)
            if issubclass(sup, StrMixIn)
            if sup.model_fields
        )
        str_field_name = next(iter(str_base_model.model_fields))
        return getattr(self, str_field_name)
