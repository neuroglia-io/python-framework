import ast
import inspect
import os
from abc import ABC, abstractclassmethod
from ast import Attribute, Name, NodeTransformer, expr
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar


T = TypeVar('T')
''' Represents the type of data associated to a queryable '''


class QueryProvider(ABC):
    ''' Defines the fundamentals of a service used to create and execute queries associated with the data source '''

    @abstractclassmethod
    def create_query(self, element_type: Type, expression: expr) -> 'Queryable':
        ''' Creates a new queryable based on the specified expression '''
        raise NotImplementedError()

    @abstractclassmethod
    def execute(self, expression: expr, query_type: Type) -> Any:
        ''' Executes the specified query expression '''
        raise NotImplementedError()


class Queryable(Generic[T]):
    ''' Provides functionality to evaluate queries against a specific data source '''

    def __init__(self, provider: QueryProvider, expression: Optional[expr] = None):
        self.provider = provider
        self.expression = ast.Name(id='__query') if expression is None else expression

    expression: expr
    ''' Gets the expression that is associated with the queryable '''

    provider: QueryProvider
    ''' Gets the service used to create and execute queries associated with the data source '''

    def get_element_type(self) -> Type:
        ''' Gets the type of elements to query against '''
        return self.__orig_class__.__args__[0]

    def first_or_default(self, predicate: Callable[[T], bool] = None) -> T:
        ''' Gets the first element in the sequence that matches the specified predicate, if any '''
        frame = inspect.currentframe().f_back
        frame_info = inspect.getframeinfo(frame)
        variables = {**frame.f_locals}
        lambda_src = self._get_lambda_source_code(predicate, frame_info.positions.end_col_offset)
        lambda_tree = ast.parse(lambda_src)
        lambda_expression = lambda_tree.body[0].value
        expression = VariableExpressionReplacer(variables).visit(ast.Call(func=ast.Attribute(value=self.expression, attr='first', ctx=ast.Load()), args=[lambda_expression], keywords=[]))
        query = self.provider.create_query(self.get_element_type(), expression)
        return self.provider.execute(query.expression, T)

    def first(self, predicate: Callable[[T], bool] = None) -> T:
        ''' Gets the first element in the sequence that matches the specified predicate, if any '''
        result = self.first_or_default(predicate)
        if result is None and T != None:
            raise Exception("No match")
        return result

    def last_or_default(self, predicate: Callable[[T], bool] = None) -> T:
        ''' Gets the last element in the sequence that matches the specified predicate, if any '''
        frame = inspect.currentframe().f_back
        frame_info = inspect.getframeinfo(frame)
        variables = {**frame.f_locals}
        lambda_src = self._get_lambda_source_code(predicate, frame_info.positions.end_col_offset)
        lambda_tree = ast.parse(lambda_src)
        lambda_expression = lambda_tree.body[0].value
        expression = VariableExpressionReplacer(variables).visit(ast.Call(func=ast.Attribute(value=self.expression, attr='last', ctx=ast.Load()), args=[lambda_expression], keywords=[]))
        query = self.provider.create_query(self.get_element_type(), expression)
        return self.provider.execute(query.expression, T)

    def last(self, predicate: Callable[[T], bool] = None) -> T:
        ''' Gets the last element in the sequence that matches the specified predicate, if any '''
        result = self.last_or_default(predicate)
        if result is None and T != None:
            raise Exception("No match")
        return result

    def order_by(self, selector: Callable[[T], Any]):
        ''' Orders the sequence using the specified attribute '''
        selector_source = self._get_lambda_source_code(selector)
        selector_tree = ast.parse(selector_source)
        selector_lambda_expression = selector_tree.body[0].value
        if not isinstance(selector_lambda_expression.body, Attribute):
            raise Exception("The specified expression must be of type Attribute")
        expression = ast.Call(func=ast.Attribute(value=self.expression, attr='order_by', ctx=ast.Load()), args=[selector_lambda_expression], keywords=[])
        return self.provider.create_query(self.get_element_type(), expression)

    def order_by_descending(self, selector: Callable[[T], Any]):
        ''' Orders the sequence in a descending fashion using the specified attribute '''
        selector_source = self._get_lambda_source_code(selector)
        selector_tree = ast.parse(selector_source)
        selector_lambda_expression = selector_tree.body[0].value
        if not isinstance(selector_lambda_expression.body, Attribute):
            raise Exception("The specified expression must be of type Attribute")
        expression = ast.Call(func=ast.Attribute(value=self.expression, attr='order_by_descending', ctx=ast.Load()), args=[selector_lambda_expression], keywords=[])
        return self.provider.create_query(self.get_element_type(), expression)

    def select(self, selector: Callable[[T], Any]):
        ''' Projects each element of a sequence into a new form '''
        frame = inspect.currentframe().f_back
        variables = {**frame.f_locals}
        selector_source = self._get_lambda_source_code(selector)
        selector_tree = ast.parse(selector_source)
        selector_lambda_expression = selector_tree.body[0].value
        if not isinstance(selector_lambda_expression.body, Attribute) and not isinstance(selector_lambda_expression.body, ast.List):
            raise Exception("The specified expression must be of type Attribute or List[Attribute]")
        expression = VariableExpressionReplacer(variables).visit(ast.Call(func=ast.Attribute(value=self.expression, attr='select', ctx=ast.Load()), args=[selector_lambda_expression], keywords=[]))
        return self.provider.create_query(self.get_element_type(), expression)

    def skip(self, amount: int):
        ''' Bypasses a specified number of elements in a sequence and then returns the remaining elements. '''
        expression = ast.Call(func=ast.Attribute(value=self.expression, attr='skip', ctx=ast.Load()), args=[ast.Constant(value=amount)], keywords=[])
        return self.provider.create_query(self.get_element_type(), expression)

    def take(self, amount: int):
        ''' Selects a specified amount of contiguous elements from the start of a sequence '''
        expression = ast.Call(func=ast.Attribute(value=self.expression, attr='take', ctx=ast.Load()), args=[ast.Constant(value=amount)], keywords=[])
        return self.provider.create_query(self.get_element_type(), expression)

    def where(self, predicate: Callable[[T], bool]) -> 'Queryable[T]':
        ''' Filters a sequence of values based on a predicate. '''
        frame = inspect.currentframe().f_back
        frame_info = inspect.getframeinfo(frame)
        variables = {**frame.f_locals}
        lambda_src = self._get_lambda_source_code(predicate, frame_info.positions.end_col_offset)
        lambda_tree = ast.parse(lambda_src)
        lambda_expression = lambda_tree.body[0].value
        expression = VariableExpressionReplacer(variables).visit(ast.Call(func=ast.Attribute(value=self.expression, attr='where', ctx=ast.Load()), args=[lambda_expression], keywords=[]))
        return self.provider.create_query(self.get_element_type(), expression)

    def to_list(self) -> List[T]:
        ''' Executes the queryable '''
        return self.provider.execute(self.expression, List)

    def __str__(self) -> str: return ast.unparse(self.expression)

    def _get_lambda_source_code(self, function: Callable, max_col_offset: int):
        ''' Gets the source code of the specified lambda 

            Args:
                function (Callable): The lambda to get the source code of
                max_col_offset (int): The maximum column offset to walk the AST tree for the target lamba

            Notes:
                Credits to https://gist.github.com/Xion/617c1496ff45f3673a5692c3b0e3f75a
        '''
        source_lines, _ = inspect.getsourcelines(function)
        if len(source_lines) != 1:
            return None
        source_text = os.linesep.join(source_lines).strip()
        source_ast = ast.parse(source_text)
        lambda_node = next((node for node in ast.walk(source_ast) if isinstance(node, ast.Lambda) and node.col_offset <= max_col_offset), None)
        if lambda_node is None:
            return None
        lambda_text = source_text[lambda_node.col_offset:lambda_node.end_col_offset]
        return lambda_text


class VariableExpressionReplacer(NodeTransformer):

    def __init__(self, variables: Dict[str, Any]):
        super().__init__()
        self.variables = variables

    variables: Dict[str, Any] = dict[str, Any]()

    def visit_Name(self, node: Name) -> Any:
        if not node.id in self.variables.keys():
            return node
        value = self.variables[node.id]
        return ast.Constant(value)
