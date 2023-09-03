from typing import Any, Iterator

from pydantic import BaseModel, RootModel

__all__ = ["Element", "StrMixIn", "StrTypes", "StrRoot", "StrRecord"]

Element = Any  # TODO: annotate it properly as forward ref to TypeVar(bound=PageElement)
# Perhaps possible once I also extract the pre-setup type table into 1 place?


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


class StrRoot(StrMixIn, RootModel):
    """
    A very string-like single field model that can be compared, hashed, and indexed.
    By default its `__str__` representation is the value of its field.
    """

    root: str

    def __str__(self) -> str:
        return self.root


class StrRecord(StrMixIn, BaseModel):
    """
    A fairly string-like model that can be compared, hashed, and indexed.
    By default its `__str__` representation is the value of its first field.
    """

    def __str__(self) -> str:
        return getattr(self, next(iter(self.model_fields)))
