from abc import ABC, abstractclassmethod
from ast import And, Attribute, BoolOp, Call, Compare, Constant, Eq, Gt, GtE, In, Is, IsNot, Lambda, Lt, LtE, Name, Not, NotEq, NotIn, Or, Subscript, USub, UnaryOp, boolop, cmpop, expr
import ast
from dataclasses import dataclass
import importlib
import inspect
from pymongo import MongoClient
from pymongo.collection import Collection
from typing import Callable, Dict, Generic, List, Optional, Type, TypeVar
from pymongo.cursor import Cursor
from pymongo.database import Database


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
        self.expression = ast.Constant(value = self) if expression is None else expression

    expression: expr
    ''' Gets the expression that is associated with the queryable '''

    provider: QueryProvider
    ''' Gets the service used to create and execute queries associated with the data source '''
    
    def get_element_type(self) -> Type: return self.__orig_class__.__args__[0]

    def where(self, predicate: Callable[[T], bool]) -> 'Queryable[T]':
        
        element_type = self.get_element_type()
        element_type_qualified_name = f'{element_type.__module__}.{element_type.__name__}'

        predicate_source = inspect.getsource(predicate)
        predicate_tree = ast.parse(predicate_source)
        predicate_expression = predicate_tree.body[0].value     
        predicate_lambda_expression = predicate_expression.args[0]
        predicate_lambda_argument_expression = predicate_lambda_expression.args.args[0]
        predicate_lambda_argument_expression.annotation = ast.Name(element_type_qualified_name, ctx=ast.Load())
        
        func = ast.Attribute(
            value=self.expression,
            attr='where',
            ctx=ast.Load())
        args = [ self, predicate_expression ]
        keywords = []
        expression = ast.Call(
            func = func, 
            args = args,
            keywords = keywords)

        return self.provider.create_query(self.get_element_type(), expression)
    
    def to_list(self) -> List[T]: return self.provider.execute(self.expression)
 
    

class MongoQuery(Generic[T], Queryable[T]):
    
    def __init__(self, query_provider: 'MongoQueryProvider', expression : Optional[expr] = None):
        super().__init__(query_provider, expression)



class MongoQueryProvider(QueryProvider):
    
    def __init__(self, collection: Collection):
        self._collection = collection

    _collection: Collection

    def create_query(self, element_type: Type, expression : expr) -> 'Queryable': return MongoQuery[element_type](self, expression)
    
    def execute(self, expression : expr) -> any:
        translator = MongoQueryTranslator()
        context = MongoQueryEvaluationContext(self._collection.find())
        translator.translate(expression, context)
        return list(context.query)



class MongoQueryEvaluationContext:
        
    def __init__(self, query : Cursor):
        self.query = query

    query : Cursor



@dataclass
class MongoQueryEvaluationScope:
    
    context: MongoQueryEvaluationContext
  
    arguments : Dict[str, Type]
    
    parent_scope: Optional['MongoQueryEvaluationScope'] = None
   
    def get_all_arguments(self) -> Dict[str, Type]:
        arguments = dict[str, Type]() if self.parent_scope is None else self.parent_scope.get_all_arguments()
        if self.arguments is not None: arguments.update(self.arguments)
        return arguments



class MongoQueryTranslator:
    
    def translate(self, expression: expr, context: MongoQueryEvaluationContext) -> None:
        if isinstance(expression, Constant): return context.query_options
        elif isinstance(expression, Call):
            declaring_type = getattr(expression.func.value, 'id', None)
            if declaring_type is None: declaring_type = expression.args[0].__class__.__name__# extract from args if id does not exist -> chained calls
            if declaring_type != 'Queryable' and declaring_type != 'MongoQuery': raise Exception(f"The translator expects query expressions of type 'Call' to invoke only functions declared by the 'Queryable' or 'MongoQuery' types, but a function declared by '{declaring_type}' was supplied")
            function_name = expression.func.attr
            lambda_expression = expression.args[1].args[0]
            if function_name == 'where': self.translate_where_clause(lambda_expression, context)
        else: raise Exception(f"The translator expects query expressions of type 'Call' or type 'Constant', but an expression of type '{type(expression).__name__}' was supplied")
    
    def translate_where_clause(self, expression: expr, context: MongoQueryEvaluationContext) -> None:
        if not isinstance(expression, Lambda): raise Exception(f"The 'where' clause translator expects an expression of type 'Lambda', but an expression of type '{type(expression).__name__}' was supplied")
        scope = MongoQueryEvaluationScope(context, self._get_lambda_arguments(expression))
        expression = self.translate_expression(expression.body, scope)
        context.query.where(expression)
        
    def translate_expression(self, expression: expr, scope : MongoQueryEvaluationScope) -> str:
        if isinstance(expression, Attribute): return self.translate_attribute(expression, scope)
        elif isinstance(expression, BoolOp): return self.translate_bool_op(expression, scope)
        elif isinstance(expression, Call):  return self.translate_call(expression, scope)
        elif isinstance(expression, Compare): return self.translate_compare(expression, scope)
        elif isinstance(expression, Constant): return self.translate_constant(expression, scope)
        elif isinstance(expression, Name): return self.translate_name(expression, scope)
        elif isinstance(expression, Subscript): return self.translate_subscript(expression, scope)
        elif isinstance(expression, UnaryOp): return self.translate_unary_op(expression, scope)
        else: raise Exception(f"The specified expression type '{type(expression)}' is not supported in this context")
        
    def translate_attribute(self, expression: Attribute, scope: MongoQueryEvaluationScope) -> str:
        attribute_name : str = None
        attribute_path_parts = list[str]()
        try: 
            attribute_name = expression.value.id
            attribute_path_parts.append(expression.attr)
        except:
            while True:
                try:
                    attribute_name = expression.value.id
                    break
                except:
                    attribute_path_parts.append(expression.value.attr)
                    expression = expression.value
        if scope.get_all_arguments().get(attribute_name) is None: return self._evaluate(expression)
        attribute_path_parts.reverse()
        attribute_full_name = f"this.{'.'.join(attribute_path_parts)}"
        return attribute_full_name

    def translate_bool_op(self, expression: BoolOp, scope: MongoQueryEvaluationScope) -> str:
        operator = self._translate_boolop(expression.op)
        parameters = [ self.translate_expression(parameter, scope) for parameter in expression.values ]
        return f' {operator} '.join(parameters)        

    def translate_call(self, expression: Call, scope: MongoQueryEvaluationScope) -> str:
        function_name = getattr(expression.func, 'id', None)
        function_body : str
        function_args : List[str]
        if function_name is None:
            function_name = expression.func.attr
            function_body = self.translate_expression(expression.func.value, scope)
            function_args = [self.translate_expression(arg, scope) for arg in expression.args]
        else:
            function_body = self.translate_expression(expression.args[0], scope)
            function_args = [self.translate_expression(arg) for arg in expression.args[1:]]
        if function_name == 'count': return f"{function_body}.length"
        elif function_name == 'len': return f"{function_body}.length"
        elif function_name == 'lower': return f"{function_body}.toLowerCase()"
        elif function_name == 'startswith': return f"{function_body}.startsWith({function_args[0]})"
        elif function_name == 'endswith': return f"{function_body}.endsWith({function_args[0]})"
        elif function_name == 'index': return f"{function_body}.indexOf({', '.join(function_args)})"
        elif function_name == 'upper': return f"{function_body}.toUpperCase()"
        elif function_name == 'split': return f"{function_body}.split({', '.join(function_args)})"
        else: raise Exception(f"The specified function '{function_name}' is not supported in this context")
    
    def translate_compare(self, expression: Compare, scope: MongoQueryEvaluationScope) -> str:
        left = self.translate_expression(expression.left, scope)        
        right = self.translate_expression(expression.comparators[0], scope)
        operator = self._translate_cmpop(expression.ops[0])
        if operator == 'in': return f"{right}.includes({left})"
        elif operator == 'not in': return f"!{right}.includes({left})"
        else: return f"{left} {operator} {right}"

    def translate_constant(self, expression: Constant, scope: MongoQueryEvaluationScope) -> str:
        if expression.value is None: return 'null'
        if isinstance(expression.value, str): return f"'{expression.value}'"
        else: return str(expression.value)
        
    def translate_name(self, expression: Name, scope: MongoQueryEvaluationScope) -> str:
        return expression.id
    
    def translate_subscript(self, expression: Subscript, scope: MongoQueryEvaluationScope) -> str:
        source = self.translate_expression(expression.value, scope)
        slice = self.translate_expression(expression.slice, scope)
        slice_index : int = None
        try: slice_index = int(slice)
        except: pass
        if slice_index is not None and slice_index < 0: return f"{source}.slice({slice})"
        else: return f"{source}[{slice}]"
    
    def translate_unary_op(self, expression: UnaryOp, scope: MongoQueryEvaluationScope) -> str:
        operand = self.translate_expression(expression.operand, scope)
        if isinstance(expression.op, Not): return f"!({operand})"
        elif isinstance(expression.op, USub): return f"-{operand}"
        else: raise Exception(f"The specified unary operator '{type(expression.op).__name__}' is not supported in this context")

    def _get_lambda_arguments(self, expression: Lambda) -> Dict[str, Type]:
        argument_name = expression.args.args[0].arg
        argument_type_qualified_name = expression.args.args[0].annotation.id
        module_name, _, type_name = argument_type_qualified_name.rpartition('.')
        module = importlib.import_module(module_name)
        argument_type = getattr(module, type_name)
        return { argument_name: argument_type }

    def _translate_boolop(self, operator : boolop) -> str:
        switch = {
            And: '&&',
            Or: '||'
        }
        result = switch.get(type(operator))
        if result is None: raise Exception(f"The specified bool operator '{type(operator).__name__}' is not supported")
        return result

    def _translate_cmpop(self, operator : cmpop) -> str:
        switch = {
            Eq: '===',
            NotEq: '!==',
            Lt: '<',
            LtE: '<=',
            Gt: '>',
            GtE: '>=',
            In: 'in',
            NotIn: 'not in',  # todo: 'not in' is not directly translatable to JavaScript
            Is: '===',
            IsNot: '!==',
        }
        result = switch.get(type(operator))
        if result is None: raise Exception(f"The specified comparison operator '{type(operator).__name__}' is not supported")
        return result



@dataclass
class User:
    
    name: str = 'unknown'
    
    email: str = None

mongo_client = MongoClient('mongodb://localhost:27017')
collection = mongo_client.get_database('test').get_collection('users')
query_provider = MongoQueryProvider(collection)
query = MongoQuery[User](query_provider)
query = query.where(lambda user: user.name is None)
query = query.where(lambda user: user.name == 'John Doe' 
                    and user.email != None 
                    and len(user.email) > 3 
                    and user.name.lower() == 'john doe' 
                    and user.name.upper() == 'JOHN DOE' 
                    and user.name[0] == "J" 
                    and user.name.startswith('John') 
                    and user.name.endswith('Doe') 
                    and 'Doe' in user.name
                    and 'Jane' not in user.name
                    and user.name.count() > 0
                    and user.email.split('@')[-1] != 'mailinator'
                    and user.name.index('J') == 0)
results = query.to_list()

query = query.where(lambda user: user.name == 'Jane Doe' and user.email != None and len(user.email) > 3)
results = query.to_list()

print('ok')