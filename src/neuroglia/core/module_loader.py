import importlib
import sys
from types import ModuleType


class ModuleLoader:

    @staticmethod
    def load(module_name: str) -> ModuleType:
        module = sys.modules.get(module_name, None)
        if module is None:
            module = importlib.import_module(module_name)
        return module
