import ast
from dataclasses import dataclass
from enum import Enum
import inspect
from typing import Callable, Dict, ForwardRef, Generic, List, Optional, Type, TypeVar

Expression = ForwardRef('Expression')
BinaryExpression = ForwardRef('BinaryExpression')
ConstantExpression = ForwardRef('ConstantExpression')
FunctionCallExpression = ForwardRef('FunctionCallExpression')
LambdaExpression = ForwardRef('LambdaExpression')
MemberExpression = ForwardRef('MemberExpression')
ParameterExpression = ForwardRef('ParameterExpression')

class Expression:
    
    def assign(member: MemberExpression, value: Expression) -> BinaryExpression:
        return BinaryExpression(member, BinaryOperator.ASSIGN, value)
 
    def parameter(type: Type, name: str) -> ParameterExpression:
        return ParameterExpression(type, name)

    def constant(value: any) -> ConstantExpression:
        return ConstantExpression(value)
    
    def call(function: str, source: Expression, parameters: Optional[List[Expression]] = None) -> FunctionCallExpression:
        return FunctionCallExpression(function, source, parameters)
    
    def anonymous_function(body: Expression, parameters: Optional[List[Expression]] = None, return_type: Optional[Type] = None) -> LambdaExpression:
        return LambdaExpression(body, parameters, return_type)


@dataclass
class ParameterExpression:
   
    name: str

    type: Type
    


@dataclass
class ConstantExpression:
    
    value: any



class BinaryOperator(Enum):
    '''
    Enumerates all supported binary operators
    '''
    ADD = '+'                       # Addition
    SUBTRACT = '-'                  # Subtraction
    MULTIPLY = '*'                  # Multiplication
    DIVIDE = '/'                    # Division
    MODULO = '%'                    # Modulus
    POWER = '**'                    # Power (exponentiation)
    BITWISE_AND = '&'               # Bitwise AND
    BITWISE_OR = '|'                # Bitwise OR
    BITWISE_XOR = '^'               # Bitwise XOR
    LEFT_SHIFT = '<<'               # Left shift
    RIGHT_SHIFT = '>>'              # Right shift
    EQUAL = '=='                    # Equal to
    NOT_EQUAL = '!='                # Not equal to
    LESS_THAN = '<'                 # Less than
    LESS_THAN_OR_EQUAL = '<='       # Less than or equal to
    GREATER_THAN = '>'              # Greater than
    GREATER_THAN_OR_EQUAL = '>='    # Greater than or equal to
    LOGICAL_AND = '&&'              # Logical AND
    LOGICAL_OR = '||'               # Logical OR
    NULL_COALESCE = '??'            # Null-coalescing operator
    ASSIGN = '='                    # Assignment operator



@dataclass
class MemberExpression:
    
    source: Expression
    
    member: str


@dataclass
class FunctionCallExpression:
    
    function: str

    source: Expression
    
    parameters: Optional[List[Expression]] = None


@dataclass
class BinaryExpression:
    
    left: Expression
    
    operator: BinaryOperator

    right: Expression

TArgs = TypeVar('TArgs', bound=List[Type])
TReturn = TypeVar('TReturn')

@dataclass
class LambdaExpression(Generic[TArgs, TReturn]):
    
    body: Expression

    parameters: Optional[List[Expression]] = None
    
    return_type: Optional[Type] = None

    def compile(self):
        source_generator = ExpressionSourceGenerator()
        source = source_generator.generate(self)
        code_unit = {}
        exec(source, None, code_unit)
        function_name = f"{ExpressionSourceGenerator._function_name_prefix}{1}"
        return code_unit[function_name]
    

class ExpressionSourceGenerator:
    
    _function_name_prefix: str = 'anonymous_function_'
    _declared_parameters : List[str] = []
    _declared_functions_count : int = 0

    def generate(self, expression: Expression) -> str:
        if isinstance(expression, ParameterExpression): return self.generate_parameter(expression)
        elif isinstance(expression, ConstantExpression): return self.generate_constant(expression)
        elif isinstance(expression, MemberExpression): return self.generate_member(expression)
        elif isinstance(expression, FunctionCallExpression): return self.generate_function_call(expression)
        elif isinstance(expression, BinaryExpression): return self.generate_binary(expression)
        elif isinstance(expression, LambdaExpression): return self.generate_lambda(expression)
        else: raise Exception(f"The specified expression type '{type(expression).__name__}' is not supported")
        
    def generate_parameter(self, expression: ParameterExpression) -> str:
        if expression.name in self._declared_parameters: return expression.name
        self._declared_parameters.append(expression.name)
        return f"{expression.name}: {expression.type.__name__}"

    def generate_constant(self, expression: ConstantExpression):
        return None if expression.value is None else f"'{expression.value}'" if isinstance(expression.value, str) else expression.value
    
    def generate_member(self, expression: MemberExpression) -> str:
        source = self.generate(expression.source)
        return f"{source}.{expression.member}"
    
    def generate_function_call(self, expression: FunctionCallExpression) -> str:
         source = self.generate(expression.source) 
         parameters = "" if expression.parameters is None or len(expression.parameters) < 1 else ", ".join([self.generate(parameter) for parameter in expression.parameters])
         return f"{source}.{expression.function}({parameters})"

    def generate_binary(self, expression: BinaryExpression) -> str:
        left = self.generate(expression.left)
        right = self.generate(expression.right)
        return f"{left} {expression.operator.value} {right}"
    
    def generate_lambda(self, expression: LambdaExpression) -> str:
        parameters = "" if expression.parameters is None or len(expression.parameters) < 1 else ", ".join([self.generate(parameter) for parameter in expression.parameters])
        body = self.generate(expression.body)
        self._declared_functions_count += 1
        return f"def {self._function_name_prefix}{self._declared_functions_count}({parameters}){'' if expression.return_type is None else f' -> {expression.return_type.__name__} '}:\n\t{'' if expression.return_type is None else 'return '}{body}"


class LambdaParser:
    @staticmethod
    def parse_lambda(lambda_str, param_type: Type):
        lambda_ast = ast.parse(lambda_str)
        lambda_node = lambda_ast.body[0].value  # Extract the lambda node

        if isinstance(lambda_node, ast.Lambda):
            parameters = [ParameterExpression(arg.arg, param_type) for arg in lambda_node.args.args]

            if isinstance(lambda_node.body, ast.Attribute):
                source = ParameterExpression(lambda_node.body.value.id, param_type)
                member = lambda_node.body.attr
                return MemberExpression(source, member)

            elif isinstance(lambda_node.body, ast.Call):
                function = lambda_node.body.func.value.id
                source = ParameterExpression(lambda_node.body.func.value.id, param_type)
                parameters = [ParameterExpression(arg.value, None) for arg in lambda_node.body.args]
                return FunctionCallExpression(function, source, parameters)

        raise ValueError("Unsupported lambda expression")


class LambdaExpressionParser(Generic[TArgs, TReturn]):
    
    parameter_map: Dict[str, Type]

    def parse(self, code: str) -> LambdaExpression:
        lambda_ast = ast.parse(code)
        lambda_node = lambda_ast.body[0].value      

        if not isinstance(lambda_node, ast.Lambda): raise Exception('The specified input is not the code of a lambda')
        body : Expression = None
        parameter_definitions = self.__orig_class__.__args__[:-1]
        parameter_names = [arg.arg for arg in lambda_node.args.args]
        self.parameter_map = dict(zip(parameter_names, parameter_definitions))
        parameters = [ Expression.parameter(key, value) for key, value in self.parameter_map.items() ]        
        return_type = self.__orig_class__.__args__[-1]
        
        if isinstance(lambda_node.body, ast.Attribute): body = self.parse_attribute(lambda_node.body)
        elif isinstance(lambda_node.body, ast.Call): body = self.parse_call(lambda_node.body)
        elif isinstance(lambda_node.body, ast.Assign): body = self.parse_call(lambda_node.body)
        
        return Expression.anonymous_function(body, parameters, return_type)

    def parse_attribute(self, expression: ast.expr) -> Expression:
        parameter_name = expression.value.id
        parameter_type = self.parameter_map[parameter_name]
        source = ParameterExpression(parameter_name, parameter_type)
        member = expression.attr
        return MemberExpression(source, member)
        


@dataclass
class User:
    
    name: str = 'unknown'
    
    email: str = None

    def greet(self) -> str: return f"Hello, {self.name}!"

source = object.__new__(User)
parameter_expression = Expression.parameter('param', User)

member_expression = MemberExpression(parameter_expression, 'name')
assign_expression = Expression.assign(member_expression, Expression.constant('John Doe'))
lambda_expression = Expression.anonymous_function(assign_expression, [ parameter_expression ])
function = lambda_expression.compile()
result1 = function(source)

lambda_expression = Expression.anonymous_function(member_expression, [ parameter_expression ], str)
function = lambda_expression.compile()
result2 = function(source)

function_call_expression = Expression.call('greet', parameter_expression)
lambda_expression = Expression.anonymous_function(function_call_expression, [ parameter_expression ], str)
function = lambda_expression.compile()
result3 = function(source)

print('done')