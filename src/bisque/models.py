from pydantic import BaseModel

__all__ = ["StrModel"]


class StrModel(BaseModel):
    """
    Base for a string-like model that can be compared, hashed, and indexed.
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
