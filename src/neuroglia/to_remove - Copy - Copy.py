from abc import ABC
import ast
from dataclasses import dataclass
import inspect
from re import A
from typing import Callable, Dict, ForwardRef, Generic, List, Type, TypeVar
from uu import Error


T = TypeVar('T')
TResult = TypeVar('TResult')

class Queryable(Generic[T], ABC):
    
    def where(self, predicate: Callable[[T], bool]) -> 'Queryable[T]':
        ''' Filters matches using the specified predicate '''
        raise NotImplementedError()
    
    def any(self, predicate: Callable[[T], bool]) -> bool:
        ''' Determines whether or not an object matches the specified predicate '''
        raise NotImplementedError()
    
    def first(self, predicate: Callable[[T], bool]) -> T:
        ''' Returns the first object to match the specified predicate '''
        raise NotImplementedError()
    
    def last(self, predicate: Callable[[T], bool]) -> T:
        ''' Returns the last object to match the specified predicate '''
        raise NotImplementedError()
    
    def select(self, predicate: Callable[[T], TResult]) -> 'Queryable[TResult]':
        ''' Projects each element of a sequence into a new object '''
        raise NotImplementedError()
    
    def to_list() -> List[T]:
        ''' Executes the query and produces a new list containing all matches '''
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
        
        expression = self.visit(lambda_node.body)
        
    def visit(self, expression: ast.expr) -> any:
        if isinstance(expression, ast.Attribute): return self.visit_attribute(expression)
        elif isinstance(expression, ast.Call):  return self.visit_call(expression)
        elif isinstance(expression, ast.Compare): return self.visit_compare(expression)
        elif isinstance(expression, ast.UnaryOp): return self.visit_unary_op(expression)
        elif isinstance(expression, ast.BoolOp): return self.visit_bool_op(expression)
        elif isinstance(expression, ast.Name): return self.visit_name(expression)
        elif isinstance(expression, ast.Constant): return self.visit_constant(expression)
        elif isinstance(expression, ast.Subscript): return self.visit_subscript(expression)
        else: raise Exception(f"The specified expression type '{type(expression)}' is not supported")
    
    def visit_attribute(self, expression: ast.Attribute):
        attribute_name : str = None
        attribute_path_parts = list[str]()
        try: 
            attribute_name = expression.value.id
            attribute_full_name = f"{expression.value.id}.{expression.attr}"
        except:
            while True:
                try:
                    attribute_name = expression.value.id
                    break
                except:
                    attribute_path_parts.append(expression.value.attr)
                    expression = expression.value
            attribute_path_parts.reverse()
            attribute_full_name = f"{attribute_name}.{'.'.join(attribute_path_parts)}"
        if attribute_name != self._parameter_name: return self._evaluate(expression)
        return MongoFilterParameter(attribute_full_name, None, None)

    def visit_call(self, expression: ast.Call):
        function_name : str = None
        function_path_parts = list[str]()
        while True:
            try:
                function_name = expression.func.id
                break
            except:
                function_path_parts.append(expression.value.attr)
                expression = expression.value        


        function_name = expression.func.id
        argument_name = None
        try: argument_name = expression.args[0].value.id
        except Exception: pass
        
        if argument_name is None or argument_name != self._parameter_name: return self._evaluate(expression)
        
        if function_name != 'len': raise Exception(f"The specified function '{function_name}' is not supported in this context")
        
        attribute_name = expression.args[0].attr
        return MongoFilterParameter(attribute_name, None, None)
    
    def visit_compare(self, expression: ast.Compare):
        left = self.visit(expression.left)        
        right = self.visit(expression.comparators[0])
        attribute_name : str = None
        value : any = None
        if type(left) is MongoFilterParameter:
            attribute_name = left.attribute_name
            value = right
        elif type(right) is MongoAttributeFilter:
            attribute_name = right.attribute_name
            value = left
        else: raise Exception('The specified expression must have one of its components referencing an attribute')
        
        return MongoFilterParameter(attribute_name, expression.ops[0], value)    

    def visit_unary_op(self, expression: ast.UnaryOp):
        operand = self.visit(expression.operand)
        if type(expression.op) is ast.Not: 
            pass
        else: raise Exception('The specified expression must have one of its components referencing an attribute')
        pass

    def visit_bool_op(self, expression: ast.BoolOp):
        parameters = [ self.visit(parameter) for parameter in expression.values ]
        filter_parameters = [parameter for parameter in parameters if type(parameter) is MongoFilterParameter ]
        if type(expression.op) is ast.And: return MongoFilterParameter() #todo
        elif type(expression.op) is ast.Or: return MongoFilterParameter() #todo
        else: raise Error("The specified operation '{}' is not supported in the context of a bool operation")
    
    def visit_name(self, expression: ast.Name):
        pass
    
    def visit_constant(self, expression: ast.Constant):
        return expression.value
    
    def visit_subscript(self, expression: ast.Subscript):
        # todo: when checking a subscript, add a new child MongoFilterParameter to check that array has a minimum length of slice + 1
        slice = expression.slice.value
        source = self.visit(expression.value)
        if type(source) is not MongoFilterParameter: return self._evaluate(expression)
        return MongoFilterParameter(f"{source.attribute_name}.{slice}", None, None)
    
    def _evaluate(self, expression: ast.expr):
        code = compile(ast.Expression(expression), filename='<ast>', mode='eval')
        return eval(code)


@dataclass      
class MongoFilterParameter:
    
    attribute_name: str
    
    operation: ast.cmpop
    
    attribute_value: any
    
    
class MongoAttributeFilter:
    
    field_name: str

    operator: str
    
    values : List
    
class Country:
    
    country_code: str = 'BE'
    
    states = list()

@dataclass
class Address:
    
    street : str
    
    country = Country()

@dataclass
class User:
    
    name: str = 'unknown'
    
    email: str = None
    
    tickets = list()

    address = Address('foo')


query = MongoQueryable[User]()
# query = query.where(lambda user: len(len(user.tickets)) > 5)
query = query.where(lambda user: not user.address.street.country.states[0] != 'hello' and user.name is not None)

