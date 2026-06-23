"""
Type registry for dynamic type discovery and deserialization support.
Provides configurable type scanning instead of hardcoded patterns.
"""

from enum import Enum
from typing import Optional

from neuroglia.core.module_loader import ModuleLoader
from neuroglia.core.type_finder import TypeFinder


class TypeRegistry:
    """
    Registry for type discovery and caching.
    Allows configurable module scanning instead of hardcoded patterns.
    """

    def __init__(self):
        self._enum_cache: dict[str, type[Enum]] = {}
        self._registered_modules: list[str] = []
        self._cache_dirty = True

    def register_modules(self, module_names: list[str]) -> None:
        """Register modules to scan for types (enums, etc.)"""
        self._registered_modules.extend(module_names)
        self._cache_dirty = True

    def register_module(self, module_name: str) -> None:
        """Register a single module to scan for types"""
        if module_name not in self._registered_modules:
            self._registered_modules.append(module_name)
            self._cache_dirty = True

    def clear_cache(self) -> None:
        """Clear the type cache to force re-scanning"""
        self._enum_cache.clear()
        self._cache_dirty = True

    def _ensure_cache_populated(self) -> None:
        """Ensure the enum cache is populated by scanning registered modules"""
        if not self._cache_dirty:
            return

        self._enum_cache.clear()

        for module_name in self._registered_modules:
            try:
                module = ModuleLoader.load(module_name)
                # Use TypeFinder to get all Enum types from the module
                enum_types = TypeFinder.get_types(
                    module,
                    predicate=lambda t: (isinstance(t, type) and issubclass(t, Enum) and t != Enum),
                    include_sub_modules=True,
                    include_sub_packages=False,
                )

                # Cache enums by name for quick lookup
                for enum_type in enum_types:
                    self._enum_cache[enum_type.__name__] = enum_type

            except (ImportError, AttributeError) as e:
                # Silently skip modules that can't be loaded
                continue

        self._cache_dirty = False

    def find_enum_for_value(self, value: str, target_type: Optional[type] = None) -> Optional[Enum]:
        """
        Find an enum member that matches the given string value.
        Optionally prefer enums from the target type's module.
        """
        if not isinstance(value, str):
            return None

        self._ensure_cache_populated()

        # First, try to find enums in the target type's module if provided
        if target_type:
            target_module_name = getattr(target_type, "__module__", None)
            if target_module_name:
                try:
                    target_module = ModuleLoader.load(target_module_name)
                    local_enums = TypeFinder.get_types(
                        target_module,
                        predicate=lambda t: (isinstance(t, type) and issubclass(t, Enum) and t != Enum),
                        include_sub_modules=False,
                        include_sub_packages=False,
                    )

                    for enum_type in local_enums:
                        enum_member = self._try_match_enum_value(value, enum_type)
                        if enum_member:
                            return enum_member

                except (ImportError, AttributeError):
                    pass

        # Then try all cached enums
        for enum_type in self._enum_cache.values():
            enum_member = self._try_match_enum_value(value, enum_type)
            if enum_member:
                return enum_member

        return None

    def _try_match_enum_value(self, value: str, enum_type: type[Enum]) -> Optional[Enum]:
        """Try to match a string value to an enum member"""
        try:
            for enum_member in enum_type:
                if enum_member.value == value or enum_member.value == value.lower() or enum_member.name == value or enum_member.name == value.upper():
                    return enum_member
        except Exception:
            pass
        return None

    def get_registered_modules(self) -> list[str]:
        """Get list of currently registered modules"""
        return self._registered_modules.copy()

    def get_cached_enum_types(self) -> dict[str, type[Enum]]:
        """Get all cached enum types (for debugging/inspection)"""
        self._ensure_cache_populated()
        return self._enum_cache.copy()


# Global singleton instance
_global_type_registry = TypeRegistry()


def get_type_registry() -> TypeRegistry:
    """Get the global type registry instance"""
    return _global_type_registry


def register_types_module(module_name: str) -> None:
    """Convenience function to register a module globally"""
    _global_type_registry.register_module(module_name)


def register_types_modules(module_names: list[str]) -> None:
    """Convenience function to register multiple modules globally"""
    _global_type_registry.register_modules(module_names)
