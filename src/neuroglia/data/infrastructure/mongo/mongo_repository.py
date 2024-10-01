import ast
from inspect import isclass
import pymongo
from ast import NodeVisitor, expr
from dataclasses import dataclass
from neuroglia.data.queryable import T, QueryProvider, Queryable
from neuroglia.data.infrastructure.abstractions import FlexibleRepository, QueryableRepository, Repository
from neuroglia.data.abstractions import TEntity, TKey, VersionedState
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.database import Database
from typing import Any, Dict, Generic, Optional, List, Type
from neuroglia.expressions.javascript_expression_translator import JavaScriptExpressionTranslator
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.serialization.json import JsonSerializer


@dataclass
class MongoRepositoryOptions(Generic[TEntity, TKey]):
    ''' Represents the options used to configure a Mongo repository '''

    database_name: str
    ''' Gets the name of the Mongo database to use '''


class MongoQuery(Generic[T], Queryable[T]):
    ''' Represents a Mongo query '''

    def __init__(self, query_provider: 'MongoQueryProvider', expression: Optional[expr] = None):
        super().__init__(query_provider, expression)


class MongoQueryBuilder(NodeVisitor):
    ''' Represents the service used to build mongo queries '''

    def __init__(self, collection: Collection, translator: JavaScriptExpressionTranslator):
        self._collection = collection
        self._translator = translator

    _collection: Collection

    _translator: JavaScriptExpressionTranslator

    _order_by_clauses: Dict[str, int] = dict[str, int]()

    _select_clause: Optional[List[str]] = None

    _skip_clause: Optional[int] = None

    _take_clause: Optional[int] = None

    _where_clauses: List[str] = list[str]()

    def build(self, expression: expr) -> Cursor:
        self.visit(expression)
        cursor: Cursor = self._collection.find(projection=self._select_clause)
        if len(self._order_by_clauses) > 0:
            cursor = cursor.sort(self._order_by_clauses)
        if len(self._where_clauses) > 0:
            cursor = cursor.where(" && ".join(self._where_clauses))
        if self._skip_clause is not None:
            cursor = cursor.skip(self._skip_clause)
        if self._take_clause is not None:
            cursor = cursor.limit(self._take_clause)
        return cursor

    def visit_Call(self, node):
        clause = node.func.attr
        expression = node.args[0]
        self.visit(node.func.value)
        javascript = self._translator.translate(expression)
        if clause == "distinct_by":
            self._distinct_by_clauses.append(javascript.replace("this.", ""))
        elif clause == "first":
            self._where_clauses.append(javascript)
            self._take_clause = 1
        elif clause == "last":
            self._where_clauses.append(javascript)
            self._take_clause = 1
            # todo: could be anything, really
            self._order_by_clauses["created_at"] = pymongo.DESCENDING
        elif clause == "order_by":
            self._order_by_clauses[javascript.replace(
                "this.", "")] = pymongo.ASCENDING
        elif clause == "order_by_descending":
            self._order_by_clauses[javascript.replace(
                "this.", "")] = pymongo.DESCENDING
        elif clause == "select" and isinstance(expression.body, ast.List):
            self._select_clause = [self._translator.translate(
                elt).replace("this.", "") for elt in expression.body.elts]
        elif clause == "skip" and isinstance(expression, ast.Constant):
            self._skip_clause = expression.value
        elif clause == "take" and isinstance(expression, ast.Constant):
            self._take_clause = expression.value
        elif clause == "where":
            self._where_clauses.append(javascript)
        pass


class MongoQueryProvider(QueryProvider):
    ''' Represents the Mongo implementation of the QueryProvider '''

    def __init__(self, collection: Collection):
        self._collection = collection

    _collection: Collection

    def create_query(self, element_type: Type,
                     expression: expr) -> Queryable: return MongoQuery[element_type](self, expression)

    def execute(self, expression: expr, query_type: Type) -> Any:
        query = MongoQueryBuilder(
            self._collection, JavaScriptExpressionTranslator()).build(expression)
        type_ = query_type if isclass(
            query_type) or query_type == List else type(query_type)
        if issubclass(type_, List):
            return list(query)
        else:
            return next(query, None)


class MongoRepository(Generic[TEntity, TKey], QueryableRepository[TEntity, TKey]):
    ''' Represents a Mongo implementation of the repository class '''

    def __init__(self, options: MongoRepositoryOptions[TEntity, TKey], mongo_client: MongoClient, serializer: JsonSerializer):
        ''' Initializes a new Mongo repository '''
        self._options = options
        self._mongo_client = mongo_client
        self._mongo_database = self._mongo_client[self._options.database_name]
        self._serializer = serializer
        self._collection_name = None

    _options: MongoRepositoryOptions[TEntity, TKey]
    ''' Gets the options used to configure the Mongo repository '''

    _mongo_client: MongoClient
    ''' Gets the service used to interact with Mongo '''

    _mongo_database: Database
    ''' Gets the Mongo database to use '''

    _serializer: JsonSerializer
    ''' Gets the service used to serialize/deserialize to/from JSON '''

    async def contains_async(self, id: TKey) -> bool: return self._get_mongo_collection().find_one({"id": id}, projection={"_id": 1})

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        attributes_dictionary = self._get_mongo_collection().find_one({"id": id})
        if (attributes_dictionary is None):
            return None
        json = self._serializer.serialize(attributes_dictionary)
        entity = self._serializer.deserialize_from_text(json, self._get_entity_type())
        return entity

    async def add_async(self, entity: TEntity) -> TEntity:
        if await self.contains_async(entity.id) is not None:
            raise Exception(f"A {self._get_entity_type().__name__} with the specified id '{entity.id}' already exists")
        json = self._serializer.serialize_to_text(entity)
        attributes_dictionary = self._serializer.deserialize_from_text(
            json, dict)
        self._get_mongo_collection().insert_one(attributes_dictionary)
        return entity

    async def update_async(self, entity: TEntity) -> TEntity:
        if not await self.contains_async(entity.id) is not None:
            raise Exception(f"Failed to find a {self._get_entity_type().__name__} with the specified id '{entity.id}'")
        query_filter = {"id": entity.id}
        expected_version = entity.state_version if isinstance(
            entity, VersionedState) else None
        if expected_version is not None:
            query_filter["state_version"] = expected_version
        json = self._serializer.serialize_to_text(entity)
        attributes_dictionary = self._serializer.deserialize_from_text(
            json, dict)
        self._get_mongo_collection().replace_one(query_filter, attributes_dictionary)
        return entity

    async def remove_async(self, id: TKey) -> None:
        if not await self.contains_async(id) is not None:
            raise Exception(f"Failed to find a {self._get_entity_type().__name__} with the specified id '{id}'")
        self._get_mongo_collection().delete_one({"id": id})

    async def query_async(self) -> Queryable[TEntity]: return MongoQuery[TEntity](MongoQueryProvider(self._get_mongo_collection()))

    def _get_entity_type(self) -> str: return self.__orig_class__.__args__[0]

    def _get_mongo_collection(self) -> Collection:
        ''' Gets the Mongo collection to use '''
        # to get the collection_name, we need to access 'self.__orig_class__', which is not yet available in __init__, thus the need for a function
        collection_name = self._get_entity_type().__name__.lower()
        if collection_name.endswith("dto"):
            collection_name = collection_name[:-3]
        return self._mongo_database[collection_name]

    @staticmethod
    def configure(builder: ApplicationBuilderBase, entity_type: Type, key_type: Type, database_name: str) -> ApplicationBuilderBase:
        ''' Configures the specified application to use a Mongo repository implementation to manage the specified type of entity '''
        connection_string_name = "mongo"
        connection_string = builder.settings.connection_strings.get(
            connection_string_name, None)
        if connection_string is None:
            raise Exception(
                f"Missing '{connection_string_name}' connection string")
        builder.services.try_add_singleton(MongoClient, singleton=MongoClient(connection_string))
        builder.services.try_add_singleton(MongoRepositoryOptions[entity_type, key_type], singleton=MongoRepositoryOptions[entity_type, key_type](database_name))
        builder.services.try_add_singleton(Repository[entity_type, key_type], MongoRepository[entity_type, key_type])
        builder.services.try_add_singleton(QueryableRepository[entity_type, key_type], implementation_factory=lambda provider: provider.get_required_service(Repository[entity_type, key_type]))
        return builder


class FlexibleMongoRepository(MongoRepository[TEntity, TKey], FlexibleRepository[TEntity, TKey]):
    ''' Represents a Mongo implementation of the flexible repository class '''

    def __init__(self, mongo_client: MongoClient, serializer: JsonSerializer):
        ''' Initializes a new Mongo repository '''
        self._mongo_client = mongo_client
        self._database_name = "NOTSETHERE"
        self._mongo_database = self._mongo_client[self._database_name]
        self._serializer = serializer
        self._collection_name = ""

    _mongo_client: MongoClient
    ''' Gets the service used to interact with Mongo '''

    _mongo_database: Database
    ''' Gets the Mongo database to use '''

    _serializer: JsonSerializer
    ''' Gets the service used to serialize/deserialize to/from JSON '''

    _collection_name: str
    ''' Gets the name of the collection in which to CRUD the entity '''

    async def set_database(self, database: str):
        if not FlexibleMongoRepository._is_valid_database_name(database):
            raise Exception(f"Database name {database} is invalid!")
        self._database_name = database
        self._mongo_database = self._mongo_client[self._database_name]

    async def get_database(self) -> str:
        return self._database_name

    async def contains_by_collection_name_async(self, collection_name: str, id: TKey) -> bool:
        if not FlexibleMongoRepository._is_valid_collection_name(collection_name):
            raise Exception(f"Collection name {collection_name} is invalid!")
        self._collection_name = collection_name
        return self._get_mongo_collection().find_one({"id": id}, projection={"_id": 1})

    async def get_by_collection_name_async(self, collection_name: str, id: TKey) -> Optional[TEntity]:
        if not FlexibleMongoRepository._is_valid_collection_name(collection_name):
            raise Exception(f"Collection name {collection_name} is invalid!")
        self._collection_name = collection_name
        return await self.get_async(id)

    async def add_by_collection_name_async(self, collection_name: str, entity: TEntity) -> TEntity:
        if not FlexibleMongoRepository._is_valid_collection_name(collection_name):
            raise Exception(f"Collection name {collection_name} is invalid!")
        self._collection_name = collection_name
        return await self.add_async(entity)

    async def update_by_collection_name_async(self, collection_name: str, entity: TEntity) -> TEntity:
        if not FlexibleMongoRepository._is_valid_collection_name(collection_name):
            raise Exception(f"Collection name {collection_name} is invalid!")
        self._collection_name = collection_name
        return await self.update_async(entity)

    async def remove_by_collection_name_async(self, collection_name: str, id: TKey) -> None:
        if not FlexibleMongoRepository._is_valid_collection_name(collection_name):
            raise Exception(f"Collection name {collection_name} is invalid!")
        self._collection_name = collection_name
        return await self.remove_async(id)

    async def query_by_collection_name_async(self, collection_name: str) -> Queryable[TEntity]:
        return MongoQuery[TEntity](MongoQueryProvider(collection_name))

    def _get_mongo_collection(self) -> Collection:
        ''' Gets the Mongo collection to use '''
        if self._collection_name is not None and self._collection_name != "":
            return self._mongo_database[self._collection_name]
        else:
            collection_name = self._get_entity_type().__name__.lower()
            if collection_name.endswith("dto"):
                collection_name = collection_name[:-3]
            return self._mongo_database[collection_name]

    @staticmethod
    def _is_valid_database_name(database_name: str) -> bool:
        # https://www.mongodb.com/docs/manual/reference/limits/#naming-restrictions
        # max 63chars, no `/\. "$*<>:|?`
        assert len(database_name) < 64, f"Database name {database_name} is too long. Max 63chars."
        assert "/" not in database_name, f"The char / (forward slash) may not be included in the database name."
        # assert r"\ " not in database_name, f"The char \ (backward slash) may not be included in the database name."  # SyntaxWarning: invalid escape sequence
        assert "." not in database_name, f"The char . (dot) may not be included in the database name."
        assert " " not in database_name, f"Space char may not be included in the database name."
        assert '"' not in database_name, f"Double quote char may not be included in the database name."
        assert '$' not in database_name, f"Dollar sign char may not be included in the database name."
        assert '*' not in database_name, f"Asterisk char may not be included in the database name."
        assert '<' not in database_name, f"Less-than-sign char may not be included in the database name."
        assert '>' not in database_name, f"Larger-than-sign char may not be included in the database name."
        assert ':' not in database_name, f"Colon char may not be included in the database name."
        assert '|' not in database_name, f"Pipe char may not be included in the database name."
        assert '?' not in database_name, f"Question mark char may not be included in the database name."
        return True

    @staticmethod
    def _is_valid_collection_name(collection_name: str) -> bool:
        # https://www.mongodb.com/docs/manual/reference/limits/#naming-restrictions
        assert len(collection_name) < 254, f"Collection name {collection_name} is too long. Max 243chars."
        assert (collection_name[0] == '_' or collection_name[0].isalpha()), f"Collection name '{collection_name}' must start with either underscore or alphanumeric char."
        assert not collection_name[0].isdigit(), f"Collection name '{collection_name}' must start with a digit."
        assert '$' not in collection_name, f"Dollar sign char may not be included in the collection name '{collection_name}'."
        assert collection_name != "", f"Collection name '{collection_name}' must not be the empty string."
        assert "\0" not in collection_name, f"Collection name '{collection_name}' must not include the Null char."
        assert not collection_name.startswith('system'), f"Collection name '{collection_name}' must not start with the word 'system'."
        return True

    @staticmethod
    def configure(builder: ApplicationBuilderBase, entity_type: Type, key_type: Type, database_name: str) -> ApplicationBuilderBase:
        ''' Configures the specified application to use a Mongo repository implementation to manage the specified type of entity '''
        connection_string_name = "mongo"
        connection_string = builder.settings.connection_strings.get(
            connection_string_name, None)
        if connection_string is None:
            raise Exception(
                f"Missing '{connection_string_name}' connection string")
        builder.services.try_add_singleton(MongoClient, singleton=MongoClient(connection_string))
        builder.services.try_add_singleton(MongoRepositoryOptions[entity_type, key_type], singleton=MongoRepositoryOptions[entity_type, key_type](database_name))
        builder.services.try_add_singleton(Repository[entity_type, key_type], FlexibleMongoRepository[entity_type, key_type])
        builder.services.try_add_singleton(FlexibleRepository[entity_type, key_type], implementation_factory=lambda provider: provider.get_required_service(Repository[entity_type, key_type]))
        return builder
