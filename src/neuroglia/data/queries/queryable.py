from abc import ABC, abstractclassmethod
from ast import Attribute, expr
import ast
import inspect
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar


T = TypeVar('T')
''' Represents the type of data associated to a queryable '''


class QueryProvider(ABC):
    ''' Defines the fundamentals of a service used to create and execute queries associated with the data source '''
    
    @abstractclassmethod
    def create_query(element_type: Type, expression : expr) -> 'Queryable':
        ''' Creates a new queryable based on the specified expression '''
        raise NotImplementedError()
    
    @abstractclassmethod
    def execute(expression : expr) -> any:
        ''' Executes the specified query expression '''
        raise NotImplementedError()
   
    
class Queryable(Generic[T]):
    ''' Provides functionality to evaluate queries against a specific data source '''

    def __init__(self, provider : QueryProvider, expression : Optional[expr] = None):
        self.provider = provider
        self.expression = ast.Name(value = 'query') if expression is None else expression

    expression: expr
    ''' Gets the expression that is associated with the queryable '''

    provider: QueryProvider
    ''' Gets the service used to create and execute queries associated with the data source '''
    
    def get_element_type(self) -> Type: return self.__orig_class__.__args__[0]

    def orderby(self, attribute_selector: Callable[[T], Any]):
        element_type = self.get_element_type()
        element_type_qualified_name = f'{element_type.__module__}.{element_type.__name__}'
        
        attribute_selector_source = inspect.getsource(attribute_selector)
        attribute_selector_tree = ast.parse(attribute_selector_source)
        attribute_selector_expression = attribute_selector_tree.body[0].value     
        attribute_selector_lambda_expression = attribute_selector_expression.args[0]
        if not isinstance(attribute_selector_lambda_expression.body, Attribute): raise Exception("The specified expression must be of type Attribute")
        
        attribute_selector_lambda_argument_expression = attribute_selector_lambda_expression.args.args[0]
        attribute_selector_lambda_argument_expression.annotation = ast.Name(element_type_qualified_name, ctx=ast.Load())
        
        func = ast.Attribute(
            value=self.expression,
            attr='orderby',
            ctx=ast.Load())
        args = [ attribute_selector_lambda_expression ]
        keywords = []
        expression = ast.Call(
            func = func, 
            args = args,
            keywords = keywords)

        return self.provider.create_query(self.get_element_type(), expression)
    
    def orderby_descending(self, attribute_selector: Callable[[T], Any]):
        element_type = self.get_element_type()
        element_type_qualified_name = f'{element_type.__module__}.{element_type.__name__}'
        
        attribute_selector_source = inspect.getsource(attribute_selector)
        attribute_selector_tree = ast.parse(attribute_selector_source)
        attribute_selector_expression = attribute_selector_tree.body[0].value     
        attribute_selector_lambda_expression = attribute_selector_expression.args[0]
        if not isinstance(attribute_selector_lambda_expression.body, Attribute): raise Exception("The specified expression must be of type Attribute")
        
        attribute_selector_lambda_argument_expression = attribute_selector_lambda_expression.args.args[0]
        attribute_selector_lambda_argument_expression.annotation = ast.Name(element_type_qualified_name, ctx=ast.Load())
        
        func = ast.Attribute(
            value=self.expression,
            attr='orderby_descending',
            ctx=ast.Load())
        args = [ attribute_selector_lambda_expression ]
        keywords = []
        expression = ast.Call(
            func = func, 
            args = args,
            keywords = keywords)

        return self.provider.create_query(self.get_element_type(), expression)

    def where(self, predicate: Callable[[T], bool]) -> 'Queryable[T]':
        
        element_type = self.get_element_type()
        element_type_qualified_name = f'{element_type.__module__}.{element_type.__name__}'
        predicate_source = inspect.getsource(predicate).strip()
        predicate_tree = ast.parse(predicate_source)
        predicate_expression = predicate_tree.body[0].value     
        predicate_lambda_expression = predicate_expression.args[0]
        predicate_lambda_argument_expression = predicate_lambda_expression.args.args[0]
        predicate_lambda_argument_expression.annotation = ast.Name(element_type_qualified_name, ctx=ast.Load())
        
        func = ast.Attribute(
            value=self.expression,
            attr='where',
            ctx=ast.Load())
        args = [ predicate_lambda_expression ]
        keywords = []
        expression = ast.Call(
            func = func, 
            args = args,
            keywords = keywords)

        return self.provider.create_query(self.get_element_type(), expression)
    
    def to_list(self) -> List[T]: return self.provider.execute(self.expression)
 