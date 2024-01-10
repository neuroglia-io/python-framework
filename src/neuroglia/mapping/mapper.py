from typing import Any, Generic, List, Optional, Type, TypeVar

TSource = TypeVar("TSource")
TDestination = TypeVar("TDestination")


class Mapper:
    

    def map(self, source : Any, destination_type: Type):
        destination = object.__new__(destination_type)
        destination.__dict__ = source.__dict__
        return destination