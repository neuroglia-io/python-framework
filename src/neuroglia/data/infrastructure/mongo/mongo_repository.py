from dataclasses import dataclass
from typing import Generic, Optional, List
from pymongo.database import Database
from neuroglia.data.infrastructure.abstractions import QueryableRepository
from neuroglia.data.abstractions import TEntity, TKey, VersionedState
from pymongo import MongoClient
from pymongo.collection import Collection

@dataclass
class MongoRepositoryOptions(Generic[TEntity, TKey]):
    ''' Represents the options used to configure a Mongo repository '''
    
    database_name: str
    ''' Gets the name of the Mongo database to use '''

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
    
    def contains(self, id: TKey) -> bool: return self._get_mongo_collection().find_one({ 'id': id }, projection={'_id': 1})
   
    def get(self, id: TKey) -> Optional[TEntity]:
        dict = self._get_mongo_collection().find_one({ 'id': id })
        if(dict is None): return None
        entity = object.__new__(self.__orig_class__.__args__[0])
        entity.__dict__ = dict
        return entity

    def add(self, entity: TEntity) -> TEntity:
        if self.contains(entity.id) != None: raise Exception(f"A {self._get_entity_name()} with the specified id '{entity.id}' already exists")
        self._get_mongo_collection().insert_one(entity.__dict__)
        return entity;

    def update(self, entity: TEntity) -> TEntity:
        if not self.contains(entity.id) != None: raise Exception(f"Failed to find a {self._get_entity_name()} with the specified id '{entity.id}'")
        query_filter = { 'id': entity.id }
        expected_version = entity.state_version if isinstance(entity, VersionedState) else None
        if expected_version is not None: query_filter['state_version'] = expected_version
        self._get_mongo_collection().replace_one(query_filter, entity.__dict__)
        return entity

    def remove(self, id: TKey) -> None:
         if not self.contains(id) != None: raise Exception(f"Failed to find a {self._get_entity_name()} with the specified id '{id}'")
         self._get_mongo_collection().delete_one({ 'id': id })
        
    def query(self) -> List[TEntity]:
        raise NotImplementedError()
    
    def _get_entity_name(self) -> str: return self.__orig_class__.__args__[0].__name__

    def _get_mongo_collection(self) -> Collection:
        ''' Gets the Mongo collection to use '''
         # to get the collection_name, we need to access 'self.__orig_class__', which is not yet available in __init__, thus the need for a function
        collection_name = self._get_entity_name().lower()
        return self._mongo_database[collection_name]