from typing import List
from neuroglia.core import TypeExtensions
from neuroglia.core.operation_result import OperationResult
from neuroglia.mediation.mediator import RequestHandler
from samples.openbank.application.queries.generic import GetByIdQuery, GetByIdQueryHandler
from tests.data import UserDto


class TestTypeExtensions:
    
    def test_get_generic_type_should_work(self):
        #arrange
        type_ = GetByIdQueryHandler[UserDto, str]
        query_type = GetByIdQuery[UserDto, str]
        expected_request_handler_type = RequestHandler[query_type, OperationResult[UserDto]]
        
        #act
        request_handler_type = TypeExtensions.get_generic_implementation(type_, RequestHandler)
        request_type = request_handler_type.__args__[0]        

        #assert
        assert request_handler_type == expected_request_handler_type
        assert request_type == query_type
    
    def test_get_generic_type_arguments_should_work(argument_names : List[str]):
        #arrange
        entity_type = UserDto
        key_type = str
        query_type = GetByIdQuery[entity_type, key_type]
        result_type = OperationResult[UserDto]
        handler_type = GetByIdQueryHandler[entity_type, key_type]
        
        #act
        generic_arguments = TypeExtensions.get_generic_arguments(handler_type)
        entity_type = generic_arguments.get("TEntity", None)
        key_type = generic_arguments.get("TKey", None)
        query_type = generic_arguments.get("TQuery", None)
        request_type = generic_arguments.get("TRequest", None)
        result_type = generic_arguments.get("TResult", None)

        #assert
        assert entity_type == entity_type
        assert key_type == key_type
        assert query_type == query_type
        assert request_type == query_type
        assert result_type == result_type
        