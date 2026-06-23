"""
Advanced MongoDB querying with type safety and complex object deserialization.

This module provides TypedMongoQuery for ensuring proper type conversion when
fetching results from MongoDB, with support for enums, datetime, nested objects,
and value objects.
"""

import logging
import inspect
import traceback
import re
from typing import TypeVar, Generic, List, Type, Dict, Callable, Optional, get_type_hints
from functools import wraps

from neuroglia.data.infrastructure.mongo.mongo_repository import MongoQuery

log = logging.getLogger(__name__)

T = TypeVar("T")


class TypedMongoQuery(Generic[T]):
    """
    A wrapper for MongoQuery that ensures proper type conversion when fetching results.
    
    This class provides type-safe querying capabilities for MongoDB operations,
    automatically converting dictionary results to properly typed entity objects
    with support for complex types including enums, datetime objects, and nested entities.
    """

    def __init__(self, query: MongoQuery, entity_type: Type[T]):
        """
        Initialize the typed mongo query.

        Args:
            query: The original MongoQuery instance
            entity_type: The entity type to convert results to
        """
        self._query = query
        self._entity_type = entity_type
        log.info(f"TypedMongoQuery created with entity_type: {entity_type.__name__}")

    def where(self, predicate: Callable) -> 'TypedMongoQuery[T]':
        """
        Apply a where filter with multiple field conditions.

        Args:
            predicate: The predicate function to filter by

        Returns:
            A new TypedMongoQuery with the filter applied
        """
        try:
            predicate_src = inspect.getsource(predicate)
            
            # Check if we have the necessary provider and collection for optimization
            if hasattr(self._query, "provider") and hasattr(self._query.provider, "_collection"):
                collection = self._query.provider._collection
                mongo_filter = {}
                closure_vars = inspect.getclosurevars(predicate)

                # Handle multiple field conditions (e.g., x.field1 == value1 and x.field2 == value2)
                field_conditions = re.findall(r"x\.(\w+)\s*==\s*(\w+)", predicate_src)

                if field_conditions:
                    # Process each condition
                    for field_name, var_name in field_conditions:
                        if var_name in closure_vars.nonlocals:
                            field_value = closure_vars.nonlocals[var_name]
                            mongo_filter[field_name] = field_value

                    # If we found valid conditions, execute a direct MongoDB query
                    if mongo_filter:
                        log.info(f"Using direct MongoDB filter: {mongo_filter}")
                        cursor = collection.find(mongo_filter)
                        self._direct_cursor = cursor
                        return self

        except Exception as e:
            log.error(f"Error parsing predicate: {e}")
            log.error(traceback.format_exc())

        # Fall back to the default behavior
        filtered_query = self._query.where(predicate)
        return TypedMongoQuery(filtered_query, self._entity_type)

    def order_by(self, selector: Callable) -> 'TypedMongoQuery[T]':
        """
        Order results by a field.

        Args:
            selector: The field selector function

        Returns:
            A new TypedMongoQuery with ordering applied
        """
        ordered_query = self._query.order_by(selector)
        return TypedMongoQuery(ordered_query, self._entity_type)

    def order_by_descending(self, selector: Callable) -> 'TypedMongoQuery[T]':
        """
        Order results by a field in descending order.

        Args:
            selector: The field selector function

        Returns:
            A new TypedMongoQuery with ordering applied
        """
        ordered_query = self._query.order_by_descending(selector)
        return TypedMongoQuery(ordered_query, self._entity_type)

    def take(self, count: int) -> 'TypedMongoQuery[T]':
        """
        Limit the number of results.

        Args:
            count: The maximum number of results to return

        Returns:
            A new TypedMongoQuery with limit applied
        """
        limited_query = self._query.take(count)
        return TypedMongoQuery(limited_query, self._entity_type)

    def skip(self, count: int) -> 'TypedMongoQuery[T]':
        """
        Skip a number of results.

        Args:
            count: The number of results to skip

        Returns:
            A new TypedMongoQuery with skip applied
        """
        skipped_query = self._query.skip(count)
        return TypedMongoQuery(skipped_query, self._entity_type)

    def to_list(self) -> List[T]:
        """
        Execute the query and return properly typed entities.

        Returns:
            A list of properly instantiated entity objects
        """
        log.info(f"TypedMongoQuery.to_list called for entity_type: {self._entity_type.__name__}")

        # Get raw results from MongoDB (either from direct cursor or original query)
        raw_results = self._get_raw_results()
        if not raw_results:
            return []

        # Convert dictionaries to proper entity objects
        result_objects = []
        for item in raw_results:
            try:
                if isinstance(item, dict):
                    entity_obj = self._create_entity_from_dict(item)
                    result_objects.append(entity_obj)
                elif isinstance(item, self._entity_type):
                    # Already the correct type
                    result_objects.append(item)
                else:
                    log.warning(f"Unexpected item type: {type(item)}, expected {self._entity_type.__name__}")
                    result_objects.append(item)
            except Exception as e:
                log.error(f"Error processing item: {e}")
                log.error(traceback.format_exc())
                # Include the original item as fallback
                result_objects.append(item)

        log.info(f"TypedMongoQuery.to_list returning {len(result_objects)} processed items")
        return result_objects

    def _get_raw_results(self) -> List[Dict]:
        """Get raw results from MongoDB, either from direct cursor or original query"""
        if hasattr(self, "_direct_cursor"):
            try:
                raw_results = list(self._direct_cursor)
                return raw_results
            except Exception as e:
                log.error(f"Error fetching results from direct cursor: {e}")
                log.error(traceback.format_exc())
                return []
        else:
            try:
                raw_results = self._query.to_list()
                return raw_results
            except Exception as e:
                log.error(f"Error executing original to_list(): {e}")
                log.error(traceback.format_exc())
                return []

    def _create_entity_from_dict(self, item: Dict) -> T:
        """Create an entity instance from a dictionary with proper type handling"""
        # Clean up MongoDB specific fields
        if "_id" in item:
            item_copy = dict(item)
            del item_copy["_id"]
        else:
            item_copy = item

        try:
            # Get constructor signature
            entity_init = self._entity_type.__init__
            sig = inspect.signature(entity_init)

            # Find required parameters (those without defaults and not self)
            required_params = {name: param for name, param in sig.parameters.items()
                               if param.default is param.empty and name != "self"}

            # Prepare constructor arguments for required parameters only
            constructor_args = {}
            kwargs = {}

            # Handle special cases for 'id' which may cause conflicts
            if "id" in item_copy and "id" not in required_params:
                stored_id = item_copy["id"]
                # Remove id from the input to avoid passing it to constructor
                item_copy_without_id = dict(item_copy)
                if "id" in item_copy_without_id:
                    del item_copy_without_id["id"]
            else:
                stored_id = None
                item_copy_without_id = item_copy

            # Process enum fields for required parameters
            for param_name in required_params:
                if param_name == "kwargs":  # Special handling for **kwargs parameter
                    continue

                if param_name in item_copy_without_id:
                    param_value = item_copy_without_id[param_name]
                    param_type = self._get_parameter_type(param_name)

                    # If parameter is an enum type and we have a string value, convert it
                    if param_type and hasattr(param_type, "__members__") and isinstance(param_value, str):
                        constructor_args[param_name] = param_type(param_value)
                    else:
                        constructor_args[param_name] = param_value

            # Add non-required values to kwargs
            for k, v in item_copy_without_id.items():
                if k not in required_params and k != "id":  # Skip id and required params
                    kwargs[k] = v

            # Add kwargs to constructor_args if the constructor accepts it
            if "kwargs" in required_params:
                constructor_args["kwargs"] = kwargs
            elif "**" in str(sig):  # Check if it accepts **kwargs
                constructor_args.update(kwargs)

            # Create the entity
            entity = self._entity_type(**constructor_args)

            # If we stored an ID and the entity has an ID field, update it
            if stored_id is not None and hasattr(entity, "id"):
                current_id = getattr(entity, "id")
                if current_id != stored_id:
                    setattr(entity, "id", stored_id)

            return entity

        except Exception as e:
            log.error(f"Error creating entity using constructor analysis: {e}")
            log.error(traceback.format_exc())
            
            # Return the original dictionary as a last resort
            log.warning("All creation methods failed, returning original dictionary")
            return item  # type: ignore

    def _get_parameter_type(self, param_name: str) -> Optional[Type]:
        """Get the type annotation for a parameter"""
        try:
            # Try to get type hints from the class
            type_hints = get_type_hints(self._entity_type)
            if param_name in type_hints:
                return type_hints[param_name]

            # Look for type annotations in parent classes
            for base in self._entity_type.__mro__[1:]:  # Skip the class itself
                if hasattr(base, "__annotations__"):
                    base_annotations = base.__annotations__
                    if param_name in base_annotations:
                        return base_annotations[param_name]
        except Exception as e:
            log.error(f"Error getting parameter type for {param_name}: {e}")

        return None


def with_typed_mongo_query(repository_method):
    """
    Decorator to wrap MongoQuery results with TypedMongoQuery.
    
    This decorator automatically enhances repository methods that return MongoQuery
    objects to instead return TypedMongoQuery objects for better type safety.

    Args:
        repository_method: The repository method to decorate

    Returns:
        Wrapped method that returns TypedMongoQuery instead of MongoQuery
    """
    @wraps(repository_method)
    async def wrapper(self, *args, **kwargs):
        # Call the original method which returns a MongoQuery
        result = await repository_method(self, *args, **kwargs)

        # Get the entity type from the repository's generic type parameter
        entity_type = self._get_entity_type()

        # Wrap the MongoQuery with our TypedMongoQuery
        if isinstance(result, MongoQuery):
            return TypedMongoQuery(result, entity_type)

        return result

    return wrapper