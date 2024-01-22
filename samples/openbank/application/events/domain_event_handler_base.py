from typing import Generic, Type, TypeVar
from neuroglia.data.abstractions import Identifiable, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper

TWriteModel = TypeVar("TWriteModel", bound=Identifiable)
''' The type of the model focused on write operations that is used to create/update/delete the state of the system, and enforce business rules '''

TReadModel = TypeVar("TReadModel", bound=Identifiable)
''' The type of the model used to provide optimized and denormalized views of the data for efficient read operations '''

class DomainEventHandlerBase(Generic[TWriteModel, TReadModel, TKey]):
    ''' Represents the base class for all services used to handle domain events '''
    
    def __init__(self, mediator: Mediator, mapper : Mapper, write_models: Repository[TWriteModel, str], read_models: Repository[TReadModel, str]):
        self.mediator = mediator
        self.mapper = mapper
        self.write_models = write_models
        self.read_models = read_models
        
    mediator : Mediator
    ''' Gets the service used to mediate calls '''
    
    mapper : Mapper
    ''' Gets the service used to map objects '''
    
    write_models: Repository[TWriteModel, str]
    ''' Gets the repository used to manage entities of a specific write model type '''
    
    read_models: Repository[TReadModel, str]
    ''' Gets the repository used to manage entities of a specific read model type '''
    
    def _get_write_model_type(self) -> Type:
        domain_event_handler_base_type = next(base for base in self.__orig_bases__ if base.__name__ == "DomainEventHandlerBase")
        return domain_event_handler_base_type.__args__[0]

    def _get_read_model_type(self) -> Type: 
        domain_event_handler_base_type = next(base for base in self.__orig_bases__ if base.__name__ == "DomainEventHandlerBase")
        return domain_event_handler_base_type.__args__[1]
    
    async def get_or_create_read_model_async(self, id : str):
        ''' Gets or creates a new read model instance for the write model with the specified id '''
        write_model_type = self._get_write_model_type()
        read_model = await self.read_models.get_async(id)

        if read_model is None:
            write_model = await self.write_models.get_async(id)
            if write_model is None: raise Exception(f"Failed to find a write model instance of type '{write_model_type}' with the specified key '{id}'")
            read_model = await self._create_read_model_async(write_model)
            read_model = await self.read_models.add_async(read_model)
        return read_model

            

    async def _create_read_model_async(self, write_model : TWriteModel):
        ''' Creates a new read model for the specified write model instance '''
        read_model_type = self._get_read_model_type()
        return self.mapper.map(write_model.state, read_model_type)