import inspect
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional, get_type_hints

from neuroglia.core import ModuleLoader, TypeFinder

if TYPE_CHECKING:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase

log = logging.getLogger(__name__)


# Helper functions to deal with typing issues
def get_origin_safe(tp: Any) -> Optional[Any]:
    """Safely get the origin of a type, handling exceptions."""
    try:
        # For Python 3.8+
        return getattr(tp, "__origin__", None)
    except (AttributeError, TypeError):
        return None


def get_args_safe(tp: Any) -> tuple[Any, ...]:
    """Safely get the args of a type, handling exceptions."""
    try:
        # For Python 3.8+
        return getattr(tp, "__args__", ())
    except (AttributeError, TypeError):
        return ()


def label(name: str, value: str):
    """Represents a decorator used to add a custom label (key, value) to a class"""

    def decorator(cls):
        if "__labels__" not in dir(cls):
            cls.__labels__ = dict()
        cls.__labels__[name] = value
        return cls

    return decorator


def labels(**kwargs):
    """Represents a decorator used to add one or more custom labels to a class"""

    def decorator(cls):
        if "__labels__" not in dir(cls):
            cls.__labels__ = dict()
        for k, v in kwargs.items():
            cls.__labels__[k] = v
        return cls

    return decorator


def map_to(target_type: type):
    """Represents a decorator used to create a mapping of the marked class to a specified type"""

    def decorator(cls):
        cls.__map_to__ = target_type
        return cls

    return decorator


def map_from(source_type: type):
    """Represents a decorator used to create a mapping from a specified type to the marked class"""

    def decorator(cls):
        cls.__map_from__ = source_type
        return cls

    return decorator


class TypeMappingContext:
    """Represents the context of a type mapping"""

    def __init__(self, source: Any, source_type: type, destination_type: type):
        self.source = source
        self.source_type = source_type
        self.destination_type = destination_type

    source: Any
    """ Gets the value to map """

    source_type: type
    """ Gets the type of the value to map """

    destination_type: type
    """ Gets the type to map the source to """


class MemberMappingContext(TypeMappingContext):
    """Represents the context of a type mapping"""

    def __init__(
        self,
        source: Any,
        source_type: type,
        destination_type: type,
        member_name: str,
        source_member_value: Any,
    ):
        super().__init__(source, source_type, destination_type)
        self.member_name = member_name
        self.source_member_value = source_member_value

    member_name: str

    source_member_value: Any


class MemberMapConfiguration:
    """Represents an object used to configure the mapping of a type member"""

    def __init__(
        self,
        name: str,
        is_ignored: bool = False,
        value_converter: Optional[Callable[[MemberMappingContext], Any]] = None,
    ):
        self.name = name
        self.is_ignored = is_ignored
        self.value_converter = value_converter

    name: str
    """ Gets the name of the configured member """

    is_ignored: bool
    """ Gets a boolean indicating whether or not the member is ignored """

    value_converter: Optional[Callable[[MemberMappingContext], Any]]
    """ Gets a callable, if any, used to convert the value of the member """


class TypeMapConfiguration:
    """Represents an object used to configure the mapping of a type to another"""

    def __init__(
        self,
        source_type: type,
        destination_type: type,
        type_converter: Optional[Callable[[Any], Any]] = None,
    ):
        self.source_type = source_type
        self.destination_type = destination_type
        self.type_converter = type_converter
        self.member_configurations: list[MemberMapConfiguration] = []

    source_type: type
    """ Gets the type to convert to the specified type """

    destination_type: type
    """ Gets the type to convert source values to """

    type_converter: Optional[Callable[[TypeMappingContext], Any]]
    """ Gets the callable, if any, used to convert source instances to the configured destination type """

    def map(self, source: Any):
        """Maps the specified value to the configured destination type"""
        mapping_context = TypeMappingContext(source, self.source_type, self.destination_type)
        if self.type_converter is not None:
            return self.type_converter(mapping_context)
        source_attributes = dict([(key, value) for key, value in source.__dict__.items() if not key.startswith("_")]) if hasattr(source, "__dict__") else dict()
        destination_attributes = dict()
        # Get all declared attributes including inherited ones
        declared_attributes = []
        for cls in self.destination_type.__mro__:
            if hasattr(cls, "__annotations__"):
                declared_attributes.extend([key for key, _ in cls.__annotations__.items() if not key.startswith("_")])
        declared_attributes = list(set(declared_attributes))  # Remove duplicates

        for source_attribute_key, source_attribute_value in source_attributes.items():
            if source_attribute_key not in declared_attributes:
                continue
            member_map = next(
                (member for member in self.member_configurations if member.name == source_attribute_key),
                None,
            )
            if member_map is None:
                destination_attributes[source_attribute_key] = source_attribute_value
            elif member_map.is_ignored:
                continue
            else:
                if member_map.value_converter:
                    destination_attributes[source_attribute_key] = member_map.value_converter(
                        MemberMappingContext(
                            source,
                            self.source_type,
                            self.destination_type,
                            source_attribute_key,
                            source_attribute_value,
                        )
                    )
                else:
                    destination_attributes[source_attribute_key] = source_attribute_value
        for configured_attribute in [attr for attr in self.member_configurations if attr.name not in source_attributes.keys()]:
            if configured_attribute.is_ignored or configured_attribute.value_converter is None:
                continue
            # Safely get source value, ensuring we have a valid value to work with
            source_value = getattr(source, configured_attribute.name, None)
            if source_value is None and hasattr(source, "__dict__"):
                source_value = source.__dict__.get(configured_attribute.name, None)
            destination_attributes[configured_attribute.name] = configured_attribute.value_converter(
                MemberMappingContext(
                    source,
                    self.source_type,
                    self.destination_type,
                    configured_attribute.name,
                    source_value,
                )
            )
        destination = object.__new__(self.destination_type)
        destination.__dict__ = destination_attributes
        return destination


class TypeMapExpression:
    """Represents a type mapping expression, used to fluently build and configure a new TypeMapConfiguration"""

    def __init__(self, configuration: TypeMapConfiguration):
        self._configuration = configuration

    _configuration: TypeMapConfiguration

    def convert_using(self, converter: Callable[[TypeMappingContext], Any]) -> None:
        """Maps values using the specified converter function"""
        self._configuration.type_converter = converter

    def ignore_member(self, name: str) -> "TypeMapExpression":
        """Configures the map to ignore the specified member of the source type"""
        configuration = next(
            (member for member in self._configuration.member_configurations if member.name == name),
            None,
        )
        if configuration is None:
            self._configuration.member_configurations.append(MemberMapConfiguration(name, True))
        else:
            configuration.is_ignored = True
        return self

    def for_member(self, name: str, converter: Callable[[MemberMappingContext], Any]):
        """Configures the mapping of the specified member to use a converter function"""
        configuration = next(
            (member for member in self._configuration.member_configurations if member.name == name),
            None,
        )
        if configuration is None:
            self._configuration.member_configurations.append(MemberMapConfiguration(name, value_converter=converter))
        else:
            configuration.value_converter = converter
        return self


class MapperConfiguration:
    def __init__(self):
        """Initialize a new MapperConfiguration with isolated instance state."""
        self.type_maps: list[TypeMapConfiguration] = []

    def create_map(self, source_type: type, destination_type: type) -> TypeMapExpression:
        """Creates a new expression used to convert how to map instances of the source type to instances of the destination type"""
        configuration: Optional[TypeMapConfiguration] = next(
            (tmc for tmc in self.type_maps if tmc.source_type == source_type and tmc.destination_type == destination_type),
            None,
        )
        if configuration is None:
            configuration = TypeMapConfiguration(source_type, destination_type)
            self.type_maps.append(configuration)
        return TypeMapExpression(configuration)


class MappingProfile:
    """Represents a class used to configure a mapper"""

    def __init__(self):
        """Initialize a new MappingProfile with isolated instance state."""
        if not hasattr(self, "_configuration_actions"):
            self._configuration_actions: list[Callable[[MapperConfiguration], None]] = []

    def create_map(self, source_type: type, destination_type: type) -> TypeMapExpression:
        """Creates a new expression used to convert how to map instances of the source type to instances of the destination type"""
        # Ensure _configuration_actions is initialized
        if not hasattr(self, "_configuration_actions"):
            self._configuration_actions: list[Callable[[MapperConfiguration], None]] = []

        # Create a local config to build the map expression
        temp_config = MapperConfiguration()
        expression = temp_config.create_map(source_type, destination_type)

        def configure_map(config: MapperConfiguration) -> None:
            # Apply the configured mapping to the actual config
            actual_expression = config.create_map(source_type, destination_type)
            # Copy over any member configurations from the temp expression
            if hasattr(expression, "_configuration") and hasattr(actual_expression, "_configuration"):
                actual_expression._configuration.member_configurations.extend(expression._configuration.member_configurations)

        self._configuration_actions.append(configure_map)
        return expression

    def apply_to(self, configuration: MapperConfiguration) -> MapperConfiguration:
        """Applies the mapping profile to the specified mapper configuration"""
        for configuration_action in self._configuration_actions:
            configuration_action(configuration)
        return configuration


class Mapper:
    """Represents the service used to map objects"""

    def __init__(self, options: MapperConfiguration):
        self.options = options

    options: MapperConfiguration
    """ Gets the options used to configure the mapper """

    def map(self, source: Any, destination_type: type) -> Any:
        """
        Maps the specified value into a new instance of the destination type,
        handling nested objects recursively.

        Args:
            source: The source object to map
            destination_type: The type to map the source to

        Returns:
            An instance of the destination type populated with mapped properties
        """
        # Handle None case
        if source is None:
            return None

        # If source is already the correct type, return it
        if isinstance(source, destination_type):
            return source

        # Get the source type
        source_type = type(source)

        # Handle collection types (list, tuple, set)
        if isinstance(source, (list, tuple, set)):
            collection_origin = get_origin_safe(destination_type)
            if collection_origin is not None and collection_origin in (list, tuple, set):
                args = get_args_safe(destination_type)
                if args:
                    item_type = args[0]
                    mapped_items = [self.map(item, item_type) for item in source]

                    if collection_origin is list:
                        return mapped_items
                    elif collection_origin is tuple:
                        return tuple(mapped_items)
                    else:  # set
                        return set(mapped_items)
            # Fallback: return source as is if no proper collection type mapping is found
            return source

        # Handle dictionary types
        if isinstance(source, dict):
            dict_origin = get_origin_safe(destination_type)
            if dict_origin is not None and dict_origin is dict:
                args = get_args_safe(destination_type)
                if len(args) == 2:
                    key_type, value_type = args
                    return {self.map(k, key_type): self.map(v, value_type) for k, v in source.items()}
            # Fallback: return source as is
            return source

        # Handle primitive types
        if isinstance(source, (int, float, str, bool)) or source_type in (int, float, str, bool):
            return source

        # Find a type map for direct mapping
        type_map = next(
            (tm for tm in self.options.type_maps if tm.source_type == source_type and tm.destination_type == destination_type),
            None,
        )

        if type_map is None:
            raise Exception(f"Missing type map configuration or unsupported mapping. " f"Mapping types: {source_type.__name__} -> {destination_type.__name__}")

        # Use the type map to create the destination object
        destination = type_map.map(source)

        # After basic mapping, check for nested objects that need mapping
        if hasattr(destination, "__dict__"):
            destination_annotations = get_type_hints(destination_type) if hasattr(destination_type, "__annotations__") else {}
            self._map_nested_attributes(destination, destination_annotations)

        return destination

    def _map_nested_attributes(self, obj: Any, type_annotations: dict[str, type]) -> None:
        """
        Maps nested attributes of an object based on type annotations.

        Args:
            obj: The object whose attributes should be mapped
            type_annotations: Dictionary of attribute names to their expected types
        """
        if not hasattr(obj, "__dict__"):
            return

        for attr_name, attr_value in obj.__dict__.items():
            # Skip private attributes or None values
            if attr_name.startswith("_") or attr_value is None:
                continue

            # Get the expected type for this attribute
            expected_type = type_annotations.get(attr_name)
            if expected_type is None:
                continue

            # Handle nested object mapping
            if hasattr(attr_value, "__dict__"):
                self._map_nested_object(obj, attr_name, attr_value, expected_type)

            # Handle collection attributes (lists, etc.)
            elif isinstance(attr_value, (list, tuple, set)):
                self._map_collection(obj, attr_name, attr_value, expected_type)

            # Handle dictionary attributes
            elif isinstance(attr_value, dict):
                self._map_dictionary(obj, attr_name, attr_value, expected_type)

    def _map_nested_object(self, obj: Any, attr_name: str, attr_value: Any, expected_type: type) -> None:
        """Maps a nested object attribute if a mapping is available."""
        source_type = type(attr_value)

        # Try to find a mapping for this nested object
        for type_map in self.options.type_maps:
            if type_map.source_type == source_type and issubclass(type_map.destination_type, expected_type):
                # Map the nested object and update it
                mapped_value = self.map(attr_value, type_map.destination_type)
                setattr(obj, attr_name, mapped_value)
                break

    def _map_collection(self, obj: Any, attr_name: str, collection: Any, expected_type: type) -> None:
        """Maps items in a collection attribute."""
        # Get the item type from the collection type annotation
        args = get_args_safe(expected_type)
        if not args:
            return  # No type arguments available

        item_type = args[0]
        if not hasattr(item_type, "__annotations__"):
            return  # No need to map primitives

        # Map each item in the collection
        mapped_items = []
        for item in collection:
            # Try to find a mapping for each item
            item_source_type = type(item)
            for type_map in self.options.type_maps:
                if type_map.source_type == item_source_type and issubclass(type_map.destination_type, item_type):
                    mapped_item = self.map(item, type_map.destination_type)
                    mapped_items.append(mapped_item)
                    break
            else:
                # No mapping found, keep original
                mapped_items.append(item)

        # Update the attribute with the mapped collection
        collection_type = type(collection)
        if collection_type is list:
            setattr(obj, attr_name, mapped_items)
        elif collection_type is tuple:
            setattr(obj, attr_name, tuple(mapped_items))
        elif collection_type is set:
            setattr(obj, attr_name, set(mapped_items))

    def _map_dictionary(self, obj: Any, attr_name: str, dictionary: dict, expected_type: type) -> None:
        """Maps keys and values in a dictionary attribute."""
        args = get_args_safe(expected_type)
        if len(args) != 2:
            return  # Not a properly annotated dictionary

        key_type, value_type = args

        # Only attempt mapping for complex value types
        if not hasattr(value_type, "__annotations__"):
            return  # No need to map dictionaries with primitive values

        # Map dictionary values
        mapped_dict = {}
        for k, v in dictionary.items():
            mapped_key = k  # Usually keys are simple types

            # Try to find a mapping for the value
            v_type = type(v)
            for type_map in self.options.type_maps:
                if type_map.source_type == v_type and issubclass(type_map.destination_type, value_type):
                    mapped_value = self.map(v, type_map.destination_type)
                    mapped_dict[mapped_key] = mapped_value
                    break
            else:
                # No mapping found, keep original
                mapped_dict[mapped_key] = v

        # Update the attribute
        setattr(obj, attr_name, mapped_dict)

    @staticmethod
    def configure(builder: "ApplicationBuilderBase", modules: list[str] = list[str]()) -> "ApplicationBuilderBase":
        """Registers and configures mapping-related services to the specified service collection.

        Args:
            services (ServiceCollection): the service collection to configure
            modules (List[str]): a list containing the names of the modules to scan for MappingProfiles, which are classes used to configure the Mapper
        """
        configuration: MapperConfiguration = MapperConfiguration()
        for module in [ModuleLoader.load(module_name) for module_name in modules]:
            mapping_profile_types = TypeFinder.get_types(
                module,
                lambda cls: inspect.isclass(cls) and issubclass(cls, MappingProfile) and cls != MappingProfile,
                include_sub_packages=True,
            )
            for mapping_profile_type in mapping_profile_types:
                mapping_profile: MappingProfile = object.__new__(mapping_profile_type)
                mapping_profile.__init__()
                mapping_profile.apply_to(configuration)
        builder.services.add_singleton(MapperConfiguration, singleton=configuration)
        builder.services.add_singleton(Mapper)
        return builder
