from abc import ABC
import ast
from dataclasses import dataclass
import inspect
from typing import Callable, Dict, ForwardRef, Generic, List, TypeVar


T = TypeVar('T')

class Queryable(Generic[T], ABC):
    
    def where(self, predicate: Callable[[T], bool]) -> 'Queryable[T]':
        ''' Filters matches using the specified predicate '''
        raise NotImplementedError()
    

class MongoQueryable(Generic[T], Queryable[T]):
    
    _parameter_name: str
    _filters: Dict[str, 'List[MongoFilterParameter]'] = dict[str, 'List[MongoFilterParameter]']()

    def where(self, predicate: Callable[[T], bool]) -> Queryable[T]:
        
        code = inspect.getsource(predicate)
        lambda_ast = ast.parse(code)
        lambda_node = lambda_ast.body[0].value
        
        if not isinstance(lambda_node, ast.Lambda): lambda_node = lambda_node.args[0]
        if not isinstance(lambda_node, ast.Lambda): raise Exception('The specified predicate must be a lambda returning a boolean')

        self._parameter_name = lambda_node.args.args[0].arg
        
        self.visit(lambda_node.body)
        # if type(filter.operation) is ast.Eq: value = filter.attribute_value
        # elif type(filter.operation) is ast.NotEq: value = { "$ne": filter.attribute_value }
        # elif type(filter.operation) is ast.Gt: value = { "$gt": filter.attribute_value }
        # elif type(filter.operation) is ast.Lt: value = { "$lt": filter.attribute_value }
        # elif type(filter.operation) is ast.LtE: value = { "$gte": filter.attribute_value }
        # elif type(filter.operation) is ast.GtE: value = { "$gte": filter.attribute_value }
        # elif type(filter.operation) is ast.And: value = { "$gte": filter.attribute_value }
        # elif type(filter.operation) is ast.Or: value = { "$gte": filter.attribute_value }
        
    def visit(self, expression: ast.expr):
        if isinstance(expression, ast.Attribute): self.visit_attribute(expression)
        elif isinstance(expression, ast.Call):  self.visit_call(expression)
        elif isinstance(expression, ast.Compare): self.visit_compare(expression)
        elif isinstance(expression, ast.And): self.visit_and(expression)
        elif isinstance(expression, ast.Or): self.visit_or(expression)
        else: raise Exception(f"The specified expression type '{type(expression)}' is not supported")
    
    def visit_attribute(self, expression: ast.expr):
        attribute_name = expression.value.id
        if attribute_name != self._parameter_name:
            # store value, replace it later
            return
        self._filters.append(MongoFilterParameter(attribute_name, None, None))

    def visit_call(self, expression: ast.expr):
        function_name = expression.func.id
        argument_name = None
        try: argument_name = expression.args[0].value.id
        except Exception: pass
        if argument_name is None or argument_name != self._parameter_name: 
            code = compile(ast.Expression(expression), filename='<ast>', mode='eval')
            result = eval(code)
            # store value, replace it later
            return
        if function_name != 'len': raise Exception(f"The specified function '{function_name}' is not supported in this context")
        filter = MongoFilterParameter()
        attribute_name = expression.args[0].attr
        filters = self._filters.get(attribute_name)
        if filters is None: filters = list['MongoFilterParameter']()
        self._filters[attribute_name] = filters
        pass
    
    def visit_compare(self, expression: ast.expr):
        pass
    
    def visit_and(self, expression: ast.expr):
        pass
    
    def visit_or(self, expression: ast.expr):
        pass

@dataclass      
class MongoFilterParameter:
    
    attribute_name: str
    
    operation: ast.cmpop
    
    attribute_value: any
    



@dataclass
class User:
    
    name: str = 'unknown'
    
    email: str = None
    
    tickets = list()


query = MongoQueryable[User]()
query = query.where(lambda user: len(user.tickets))
