import json
from classy_fastapi import Routable
from fastapi import Response
from neuroglia.core.operation_result import OperationResult
from neuroglia.core.problem_details import ProblemDetails
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator


class ControllerBase(Routable):
    ''' Represents the base class of all API controllers '''
   
    def __init__(self, service_provider: ServiceProviderBase, mapper : Mapper, mediator : Mediator):
        ''' Initializes a new ControllerBase '''
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = self.__class__.__name__.replace('Controller', '').strip()
        super().__init__(prefix=f"/{self.name.lower()}", tags=[self.name])
        
    service_provider : ServiceProviderBase
    ''' Gets the current ServiceProviderBase '''
    
    mapper : Mapper
    ''' Gets the service used to map objects '''

    mediator: Mediator
    ''' Gets the service used to mediate calls '''

    name : str
    ''' Gets/sets the name of the controller, which is used to configure the controller's router. Defaults to the lowercased name of the implementing controller class, excluding the term 'Controller' '''
                
    def process(self, result: OperationResult):
        ''' Processes the specified operation result '''
        content = result.data if result.status >= 200 and result.status < 300 else result
        if content is not None: 
            content = json.dumps(content)
            media_type = "application/json"
        return Response(status_code=result.status, content=content, media_type=media_type)
    
    error_responses = {
        400: { "model": ProblemDetails, "description": "Bad Request" },
        500: { "model": ProblemDetails, "description": "Internal Server Error" },
    }
        