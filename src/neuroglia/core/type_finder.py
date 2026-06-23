import importlib
import inspect
import pkgutil
from collections.abc import Callable
from types import ModuleType
from typing import Type


class TypeFinder:
    """Represents an utility class that exposes methods to find and filter types"""

    @staticmethod
    def get_types(
        module: ModuleType,
        predicate: Callable[[type], bool] = lambda t: True,
        include_sub_modules=True,
        include_sub_packages=False,
    ) -> list[type]:
        """Recursively finds all types contained in the specified module that match the specified predicate, if any"""
        results: list[type] = list[Type]()
        results.extend([cls for _, cls in inspect.getmembers(module, inspect.isclass) if predicate(cls)])
        if include_sub_modules:
            for submodule in [submodule for _, submodule in inspect.getmembers(module, inspect.ismodule) if submodule.__name__.startswith(module.__name__)]:
                results.extend(TypeFinder.get_types(submodule, predicate, include_sub_modules, include_sub_packages))
        # todo: the following creates big problems, as it will actually (re)load, thus (re)run, imported packages <= it sucks
        if include_sub_packages:
            if hasattr(module, "__path__"):
                sub_packages = [importlib.import_module(module_name) for _, module_name, _ in pkgutil.walk_packages(module.__path__, module.__name__ + ".") if module_name.startswith(module.__name__)]
                for submodule in sub_packages:
                    results.extend(TypeFinder.get_types(submodule, predicate, include_sub_modules, include_sub_packages))
        return list(set(results))
