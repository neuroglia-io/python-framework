from typing import Dict, Type, TypeVar


class TypeExtensions:
    @staticmethod
    def get_generic_implementation(type_: type, generic_type_definition: type, generic_args: dict[str, type] = None):
        base_types = TypeExtensions._get_base_types(type_)
        base_types = [base for base in base_types if (issubclass(base.__origin__, generic_type_definition) if hasattr(base, "__origin__") else issubclass(base, generic_type_definition))]
        base_type = next(
            (base for base in base_types if base == generic_type_definition or (hasattr(base, "__origin__")) and base.__origin__ == generic_type_definition),
            None,
        )
        if hasattr(type_, "__orig_class__") and hasattr(type_.__orig_class__.__origin__, "__parameters__"):
            if generic_args is None:
                generic_args = dict[str, Type]()
            for i in range(len(type_.__orig_class__.__origin__.__parameters__)):
                name = type_.__orig_class__.__origin__.__parameters__[i].__name__
                arg_type = type_.__orig_class__.__args__[i]
                generic_args[name] = arg_type
        if hasattr(type_, "__origin__") and hasattr(type_.__origin__, "__parameters__"):
            if generic_args is None:
                generic_args = dict[str, Type]()
            for i in range(len(type_.__origin__.__parameters__)):
                name = type_.__origin__.__parameters__[i].__name__
                arg_type = type_.__args__[i]
                generic_args[name] = arg_type
        if base_type is not None:
            return TypeExtensions._substitute_generic_arguments(base_type, generic_args)
        else:
            return next(
                (implementation_type for implementation_type in [TypeExtensions.get_generic_implementation(base, generic_type_definition, generic_args) for base in base_types]),
                None,
            )

    @staticmethod
    def get_generic_arguments(type_: type, generic_arguments: dict[str, type] = None) -> dict[str, type]:
        if hasattr(type_, "__orig_class__") and hasattr(type_.__orig_class__.__origin__, "__parameters__"):
            if generic_arguments is None:
                generic_arguments = dict[str, Type]()
            for i in range(len(type_.__orig_class__.__origin__.__parameters__)):
                name = type_.__orig_class__.__origin__.__parameters__[i].__name__
                arg_type = type_.__orig_class__.__args__[i]
                generic_arguments[name] = TypeExtensions._substitute_generic_arguments(arg_type, generic_arguments)
        if hasattr(type_, "__origin__") and hasattr(type_.__origin__, "__parameters__"):
            if generic_arguments is None:
                generic_arguments = dict[str, Type]()
            for i in range(len(type_.__origin__.__parameters__)):
                name = type_.__origin__.__parameters__[i].__name__
                arg_type = type_.__args__[i]
                generic_arguments[name] = TypeExtensions._substitute_generic_arguments(arg_type, generic_arguments)
        for base_type in TypeExtensions._get_base_types(type_):
            generic_arguments = TypeExtensions.get_generic_arguments(base_type, generic_arguments)
        return generic_arguments

    @staticmethod
    def get_generic_argument(type_: type, name: str) -> Type | None:
        generic_arguments = TypeExtensions.get_generic_arguments(type_)
        return generic_arguments.get(name, None)

    @staticmethod
    def _get_base_types(type_: type) -> list[type]:
        if hasattr(type_, "__origin__") and hasattr(type_.__origin__, "__orig_bases__"):
            return type_.__origin__.__orig_bases__
        elif hasattr(type_, "__orig_bases__"):
            return type_.__orig_bases__
        else:
            return list[Type]()

    @staticmethod
    def _substitute_generic_arguments(type_: type, generic_args: Dict[str, Type] | None = None) -> type:
        if not hasattr(type_, "__parameters__") and generic_args is not None:
            if isinstance(type_, TypeVar):
                return generic_args.get(type_.__name__, None)
            else:
                return type_
        if not hasattr(type_, "__parameters__"):
            return type_
        if generic_args is None:
            return type_
        parameters = [param.__name__ for param in type_.__parameters__]
        type_args = [TypeExtensions._substitute_generic_arguments(generic_arg_value, generic_args) for generic_arg_key, generic_arg_value in generic_args.items() if generic_arg_key in parameters]
        if len(type_args) < 1:
            return type_
        # Handle generic type subscription - use dynamic getitem for type subscription
        try:
            if len(type_args) == 1:
                return getattr(type_, "__getitem__")(type_args[0])
            else:
                return getattr(type_, "__getitem__")(tuple(type_args))
        except (TypeError, AttributeError):
            return type_
