import inspect

from neuroglia.core.module_loader import ModuleLoader
from neuroglia.core.type_finder import TypeFinder
from neuroglia.mapping.mapper import MappingProfile


class Profile(MappingProfile):
    """Represents the application's mapping profile
    Where to look for any 'map_to' or 'map_from' entities that should be mapped to a Dto...
    """

    def __init__(self):
        super().__init__()
        modules = [
            "application.commands",
            "application.queries",
            "application.events.integration",
            "application.services",
        ]
        for module in [ModuleLoader.load(module_name) for module_name in modules]:
            for type_ in TypeFinder.get_types(
                module,
                lambda cls: inspect.isclass(cls) and (hasattr(cls, "__map_from__") or hasattr(cls, "__map_to__")),
            ):
                map_from = getattr(type_, "__map_from__", None)
                map_to = getattr(type_, "__map_to__", None)
                if map_from is not None:
                    self.create_map(map_from, type_)
                if map_to is not None:
                    map = self.create_map(type_, map_to)  # todo: make it work by changing how profile is used, so that it can return an expression
                    # if hasattr(type_, "__orig_bases__") and next((base for base in type_.__orig_bases__ if base.__name__ == "AggregateRoot"), None) is not None:
                    #     map.convert_using(lambda context: context.mapper.map(context.source.state, context.destination_type))
