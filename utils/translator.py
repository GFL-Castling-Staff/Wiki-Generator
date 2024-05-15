from typing import Dict

class Translator:
    __mapper = {}

    def __init__(self, mapper:Dict[str, str]) -> None:
        self.__mapper = mapper

    def get(self, left:str) -> str:
        return self.__mapper[left] if left in self.__mapper.keys() else left