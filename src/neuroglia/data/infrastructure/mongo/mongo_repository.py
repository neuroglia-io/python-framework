from ast import NodeVisitor, expr
from dataclasses import dataclass
from neuroglia.data.queries.queryable import T, QueryProvider, Queryable
from neuroglia.data.infrastructure.abstractions import QueryableRepository, Repository
from neuroglia.data.abstractions import TEntity, TKey, VersionedState
import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.database import Database
from typing import Dict, Generic, Optional, List, Type
from neuroglia.dependency_injection.service_provider import ServiceCollection

from neuroglia.expressions.javascript_expression_translator import JavaScriptExpressionTranslator


@dataclass
class MongoRepositoryOptions(Generic[TEntity, TKey]):
    ''' Represents the options used to configure a Mongo repository '''
    
    database_name: str
    ''' Gets the name of the Mongo database to use '''
 
    
class MongoQuery(Generic[T], Queryable[T]):
    
    def __init__(self, query_provider: 'MongoQueryProvider', expression : Optional[expr] = None):
        super().__init__(query_provider, expression)


class MongoQueryBuilder(NodeVisitor):
   
    def __init__(self, collection : Collection, translator : JavaScriptExpressionTranslator):
        self._collection = collection
        self._translator = translator

    _collection : Collection

    _translator : JavaScriptExpressionTranslator
    
    _select_clause : Optional[Dict];
    
    _where_clauses : List[str] = list[str]()
    
    _orderby_clauses : Dict[str, int] = dict[str, int]()

    def build(self, expression : expr) -> Cursor:
        self.visit(expression)
        cursor : Cursor = self._collection.find() #projection = None if self._select_clause is None else self._select_clause)
        where = ' && '.join(self._where_clauses)
        cursor = cursor.where(where)
        if len(self._orderby_clauses) > 0: cursor = cursor.sort(self._orderby_clauses) 
        return cursor
    
    def visit_Call(self, node):
        clause = node.func.attr
        expression = node.args[0]
        self.visit(node.func.value)
        javascript = self._translator.translate(expression)
        if clause == 'orderby': self._orderby_clauses[javascript.replace('this.', '')] = pymongo.ASCENDING
        elif clause == 'orderby_descending': self._orderby_clauses[javascript.replace('this.', '')] = pymongo.DESCENDING
        elif clause == 'select': self._select_clause = javascript
        elif clause == 'where': self._where_clauses.append(javascript)
        

class MongoQueryProvider(QueryProvider):
    
    def __init__(self, collection: Collection):
        self._collection = collection

    _collection: Collection

    def create_query(self, element_type: Type, expression : expr) -> Queryable: return MongoQuery[element_type](self, expression)
    
    def execute(self, expression : expr) -> any:
        query = MongoQueryBuilder(self._collection, JavaScriptExpressionTranslator()).build(expression)
        return list(query)


class MongoRepository(Generic[TEntity, TKey], QueryableRepository[TEntity, TKey]):
    ''' Represents a Mongo implementation of the repository class '''

    def __init__(self, options: MongoRepositoryOptions[TEntity, TKey], mongo_client: MongoClient):
        ''' Initializes a new Mongo repository '''
        self._options = options
        self._mongo_client = mongo_client
        self._mongo_database = self._mongo_client[self._options.database_name]

    _options : MongoRepositoryOptions[TEntity, TKey]
    ''' Gets the options used to configure the Mongo repository '''

    _mongo_client : MongoClient
    ''' Gets the service used to interact with Mongo '''
    
    _mongo_database: Database
    ''' Gets the Mongo database to use '''
    
    async def contains_async(self, id: TKey) -> bool: return self._get_mongo_collection().find_one({ 'id': id }, projection={'_id': 1})
   
    async def get_async(self, id: TKey) -> Optional[TEntity]:
        dict = self._get_mongo_collection().find_one({ 'id': id })
        if(dict is None): return None
        entity = object.__new__(self.__orig_class__.__args__[0])
        entity.__dict__ = dict
        return entity

    async def add_async(self, entity: TEntity) -> TEntity:
        if await self.contains_async(entity.id) != None: raise Exception(f"A {self._get_entity_name()} with the specified id '{entity.id}' already exists")
        self._get_mongo_collection().insert_one(entity.__dict__)
        return entity;

    async def update_async(self, entity: TEntity) -> TEntity:
        if not await self.contains_async(entity.id) != None: raise Exception(f"Failed to find a {self._get_entity_name()} with the specified id '{entity.id}'")
        query_filter = { 'id': entity.id }
        expected_version = entity.state_version if isinstance(entity, VersionedState) else None
        if expected_version is not None: query_filter['state_version'] = expected_version
        self._get_mongo_collection().replace_one(query_filter, entity.__dict__)
        return entity

    async def remove_async(self, id: TKey) -> None:
         if not await self.contains_async(id) != None: raise Exception(f"Failed to find a {self._get_entity_name()} with the specified id '{id}'")
         self._get_mongo_collection().delete_one({ 'id': id })
        
    async def query_async(self) -> Queryable[TEntity]: return MongoQuery[TEntity](MongoQueryProvider(self._get_mongo_collection()))
    
    def _get_entity_name(self) -> str: return self.__orig_class__.__args__[0].__name__

    def _get_mongo_collection(self) -> Collection:
        ''' Gets the Mongo collection to use '''
         # to get the collection_name, we need to access 'self.__orig_class__', which is not yet available in __init__, thus the need for a function
        collection_name = self._get_entity_name().lower()
        return self._mongo_database[collection_name]