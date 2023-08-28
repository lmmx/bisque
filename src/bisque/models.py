from pydantic import BaseModel, RootModel

__all__ = ["StrMixIn", "StrRoot", "StrRecord"]


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
