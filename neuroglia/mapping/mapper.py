import importlib
import inspect
from typing import Any, Callable, List, Type
from neuroglia.core import ModuleLoader, TypeFinder
from neuroglia.hosting.abstractions import ApplicationBuilderBase


def label(name: str, value: str):
    ''' Represents a decorator used to add a custom label (key, value) to a class'''
    def decorator(cls):
        if "__labels__" not in dir(cls):
            cls.__labels__ = dict()
        cls.__labels__[name] = value
        return cls
    return decorator


def labels(**kwargs):
    ''' Represents a decorator used to add one or more custom labels to a class'''
    def decorator(cls):
        if "__labels__" not in dir(cls):
            cls.__labels__ = dict()
        for k, v in kwargs.items():
            cls.__labels__[k] = v
        return cls
    return decorator


def map_to(target_type: Type):
    ''' Represents a decorator used to create a mapping of the marked class to a specified type '''
    def decorator(cls):
        cls.__map_to__ = target_type
        return cls
    return decorator


def map_from(source_type: Type):
    ''' Represents a decorator used to create a mapping from a specified type to the marked class '''
    def decorator(cls):
        cls.__map_from__ = source_type
        return cls
    return decorator


class TypeMappingContext:
    ''' Represents the context of a type mapping '''

    def __init__(self, source: Any, source_type: Type, destination_type: Type):
        self.source = source
        self.source_type = source_type
        self.destination_type = destination_type

    source: Any
    ''' Gets the value to map '''

    source_type: Type
    ''' Gets the type of the value to map '''

    destination_type: Type
    ''' Gets the type to map the source to '''


class MemberMappingContext(TypeMappingContext):
    ''' Represents the context of a type mapping '''

    def __init__(self, source: Any, source_type: Type, destination_type: Type, member_name: str, source_member_value: Any):
        super().__init__(source, source_type, destination_type)
        self.member_name = member_name
        self.source_member_value = source_member_value

    member_name: str

    source_member_value: Any


class MemberMapConfiguration:
    ''' Represents an object used to configure the mapping of a type member '''

    def __init__(self, name: str, is_ignored: bool = False, value_converter: Callable[[MemberMappingContext], Any] = None):
        self.name = name
        self.is_ignored = is_ignored
        self.value_converter = value_converter

    name: str
    ''' Gets the name of the configured member '''

    is_ignored: bool
    ''' Gets a boolean indicating whether or not the member is ignored '''

    value_converter: Callable[[MemberMappingContext], Any]
    ''' Gets a callable, if any, used to convert the value of the member '''


class TypeMapConfiguration:
    ''' Represents an object used to configure the mapping of a type to another '''

    def __init__(self, source_type: Type, destination_type: Type, type_converter: Callable[[Any], Any] = None):
        self.source_type = source_type
        self.destination_type = destination_type
        self.type_converter = type_converter

    source_type: Type
    ''' Gets the type to convert to the specified type '''

    destination_type: Type
    ''' Gets the type to convert source values to '''

    type_converter: Callable[[TypeMappingContext], Any]
    ''' Gets the callable, if any, used to convert source instances to the configured destination type '''

    member_configurations: List[MemberMapConfiguration] = list[MemberMapConfiguration]()
    ''' Gets a list containing objects used to configure how to map members of the configured source and destination types '''

    def map(self, source: Any):
        ''' Maps the specified value to the configured destination type '''
        mapping_context = TypeMappingContext(source, self.source_type, self.destination_type)
        if self.type_converter is not None:
            return self.type_converter(mapping_context)
        source_attributes = dict([(key, value) for key, value in source.__dict__.items() if not key.startswith('_')]) if hasattr(source, "__dict__") else dict()
        destination_attributes = dict()
        declared_attributes = [key for key, _ in self.destination_type.__annotations__.items() if not key.startswith('_')] if hasattr(self.destination_type, "__annotations__") else list[str]()
        for source_attribute_key, source_attribute_value in source_attributes.items():
            if not source_attribute_key in declared_attributes:
                continue
            member_map = next((member for member in self.member_configurations if member.name == source_attribute_key), None)
            if member_map is None:
                destination_attributes[source_attribute_key] = source_attribute_value
            elif member_map.is_ignored:
                continue
            else:
                destination_attributes[source_attribute_key] = member_map.value_converter(MemberMappingContext(source, self.source_type, self.destination_type, source_attribute_key, source_attribute_value))
        for configured_attribute in [attr for attr in self.member_configurations if attr not in source_attributes.keys()]:
            if configured_attribute.is_ignored or configured_attribute.value_converter is None:
                continue
            destination_attributes[configured_attribute.name] = configured_attribute.value_converter(MemberMappingContext(source, self.source_type, self.destination_type, configured_attribute.name, None))
        destination = object.__new__(self.destination_type)
        destination.__dict__ = destination_attributes
        return destination


class TypeMapExpression:
    ''' Represents a type mapping expression, used to fluently build and configure a new TypeMapConfiguration '''

    def __init__(self, configuration: TypeMapConfiguration):
        self._configuration = configuration

    _configuration: TypeMapConfiguration

    def convert_using(self, converter: Callable[[TypeMappingContext], Any]) -> None:
        ''' Maps values using the specified converter function '''
        self._configuration.type_converter = converter

    def ignore_member(self, name: str) -> 'TypeMapExpression':
        ''' Configures the map to ignore the specified member of the source type '''
        configuration = next((member for member in self._configuration.member_configurations if member.name == name), None)
        if configuration is None:
            self._configuration.member_configurations.append(MemberMapConfiguration(name, True))
        else:
            configuration.is_ignored = True
        return self

    def for_member(self, name: str, converter: Callable[[MemberMappingContext], Any]):
        ''' Configures the mapping of the specified member to use a converter function '''
        configuration = next((member for member in self._configuration.member_configurations if member.name == name), None)
        if configuration is None:
            self._configuration.member_configurations.append(MemberMapConfiguration(name, value_converter=converter))
        else:
            configuration.value_converter = converter
        return self


class MapperConfiguration:

    type_maps: List[TypeMapConfiguration] = list[TypeMapConfiguration]()

    def create_map(self, source_type: Type, destination_type: Type) -> TypeMapExpression:
        ''' Creates a new expression used to convert how to map instances of the source type to instances of the destination type '''
        configuration: TypeMapConfiguration = next((tmc for tmc in self.type_maps if tmc.source_type == source_type and tmc.destination_type == destination_type), None)
        if configuration is None:
            configuration = TypeMapConfiguration(source_type, destination_type)
            self.type_maps.append(configuration)
        return TypeMapExpression(configuration)


class MappingProfile:
    ''' Represents a class used to configure a mapper'''

    _configuration_actions: List[Callable[[MapperConfiguration], None]] = list[Callable[[MapperConfiguration], None]]()
    ''' Gets the mapper configuration to configure '''

    def create_map(self, source_type: Type, destination_type: Type) -> TypeMapExpression:
        ''' Creates a new expression used to convert how to map instances of the source type to instances of the destination type '''
        callable: Callable[[MapperConfiguration], None] = lambda config: config.create_map(source_type, destination_type)
        self._configuration_actions.append(callable)

    def apply_to(self, configuration: MapperConfiguration) -> MapperConfiguration:
        ''' Applies the mapping profile to the specified mapper configuration '''
        for configuration_action in self._configuration_actions:
            configuration_action(configuration)
        return configuration


class Mapper:
    ''' Represents the service used to map objects '''

    def __init__(self, options: MapperConfiguration):
        self.options = options

    options: MapperConfiguration
    ''' Gets the options used to configure the mapper '''

    def map(self, source: Any, destination_type: Type) -> Any:
        ''' Maps the specified value into a new instance of the destination type '''
        source_type = type(source)
        type_map = next((tmc for tmc in self.options.type_maps if tmc.source_type == source_type and tmc.destination_type == destination_type), None)
        if type_map is None:
            raise Exception(f"Missing type map configuration or unsupported mapping. Mapping types: {source_type.__name__} -> {destination_type.__name__}")
        destination = type_map.map(source)
        return destination

    @staticmethod
    def configure(builder: ApplicationBuilderBase, modules: List[str] = list[str]()) -> ApplicationBuilderBase:
        ''' Registers and configures mapping-related services to the specified service collection.

            Args:
                services (ServiceCollection): the service collection to configure
                modules (List[str]): a list containing the names of the modules to scan for MappingProfiles, which are classes used to configure the Mapper
        '''
        configuration: MapperConfiguration = MapperConfiguration()
        for module in [ModuleLoader.load(module_name) for module_name in modules]:
            mapping_profile_types = TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and issubclass(cls, MappingProfile) and cls != MappingProfile, include_sub_packages=True)
            for mapping_profile_type in mapping_profile_types:
                mapping_profile: MappingProfile = object.__new__(mapping_profile_type)
                mapping_profile.__init__()
                mapping_profile.apply_to(configuration)
        builder.services.add_singleton(MapperConfiguration, singleton=configuration)
        builder.services.add_singleton(Mapper)
        return builder
