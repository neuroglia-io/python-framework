import ast
from ast import And, Attribute, BoolOp, Call, Compare, Constant, Eq, Gt, GtE, In, Is, IsNot, Lambda, Lt, LtE, Name, Not, NotEq, NotIn, Or, Subscript, USub, UnaryOp, arg, boolop, cmpop, expr
import importlib
from typing import Dict, List, Type


class JavaScriptExpressionTranslator:
    ''' Represents a service used to translate ast expressions into JavaScript expressions'''

    def translate(self, expression: expr) -> str:
        ''' Translates the specified expression into a new JavaScript expression '''
        if isinstance(expression, arg): return self._translate_arg(expression)
        elif isinstance(expression, Attribute): return self._translate_attribute(expression)
        elif isinstance(expression, BoolOp): return self._translate_bool_op(expression)
        elif isinstance(expression, Call):  return self._translate_call(expression)
        elif isinstance(expression, Compare): return self._translate_compare(expression)
        elif isinstance(expression, Constant): return self._translate_constant(expression)
        elif isinstance(expression, Lambda): return self._translate_lambda(expression)
        elif isinstance(expression, Name): return self._translate_name(expression)
        elif isinstance(expression, Subscript): return self._translate_subscript(expression)
        elif isinstance(expression, UnaryOp): return self._translate_unary_op(expression)
        elif isinstance(expression, ast.List): return self._translate_list(expression)
        else: raise Exception(f"The specified expression type '{type(expression)}' is not supported in this context")

    def _translate_arg(self, expression: arg) -> str: 
        return expression.arg

    def _translate_attribute(self, expression: Attribute) -> str:
        attribute_name : str = None
        attribute_path_parts = list[str]()
        if isinstance(expression.value, Constant):
            return self.translate(Constant(getattr(expression.value.value, expression.attr)))
        else:
            try: 
                attribute_name = expression.value.id
                attribute_path_parts.append(expression.attr)
            except:
                while True:
                    try:
                        attribute_name = expression.value.id
                        break
                    except:
                        attribute_path_part = self.translate(expression.value)
                        attribute_path_parts.append(attribute_path_part)
                        expression = expression.value
            #if scope.get_all_arguments().get(attribute_name) is None: return self._evaluate(expression) #todo
            attribute_path_parts.reverse()
            attribute_full_name = f"this.{'.'.join(attribute_path_parts)}"
            return attribute_full_name

    def _translate_bool_op(self, expression: BoolOp) -> str:
        operator = self._translate_boolop(expression.op)
        parameters = [ self.translate(parameter) for parameter in expression.values ]
        return f' {operator} '.join(parameters)        

    def _translate_call(self, expression: Call) -> str:
        function_name = getattr(expression.func, 'id', None)
        function_body : str
        function_args : List[str]
        if function_name is None:
            function_name = expression.func.attr
            function_body = self.translate(expression.func.value)
            function_args = [self.translate(arg) for arg in expression.args]
        else:
            function_body = self.translate(expression.args[0])
            function_args = [self.translate(arg) for arg in expression.args[1:]]
        if function_name == 'count': return f"{function_body}.length"
        elif function_name == 'len': return f"{function_body}.length"
        elif function_name == 'lower': return f"{function_body}.toLowerCase()"
        elif function_name == 'startswith': return f"{function_body}.startsWith({function_args[0]})"
        elif function_name == 'endswith': return f"{function_body}.endsWith({function_args[0]})"
        elif function_name == 'index': return f"{function_body}.indexOf({', '.join(function_args)})"
        elif function_name == 'upper': return f"{function_body}.toUpperCase()"
        elif function_name == 'split': return f"{function_body}.split({', '.join(function_args)})"
        else: raise Exception(f"The specified function '{function_name}' is not supported in this context")
    
    def _translate_compare(self, expression: Compare) -> str:
        left = self.translate(expression.left)        
        right = self.translate(expression.comparators[0])
        operator = self._translate_cmpop(expression.ops[0])
        if operator == 'in': return f"{right}.includes({left})"
        elif operator == 'not in': return f"!{right}.includes({left})"
        else: return f"{left} {operator} {right}"

    def _translate_constant(self, expression: Constant) -> str:
        if expression.value is None: return 'null'
        if isinstance(expression.value, str): return f"'{expression.value}'"
        else: return str(expression.value)
        
    def _translate_lambda(self, expression: Lambda) -> str:
        body = self.translate(expression.body)
        return body
    
    def _translate_list(self, expression: ast.List) -> str:
        return f"[ {', '.join([self.translate(expression) for expression in expression.elts])} ]"

    def _translate_name(self, expression: Name) -> str:
        return "this"
    
    def _translate_subscript(self, expression: Subscript) -> str:
        source = self.translate(expression.value)
        slice = self.translate(expression.slice)
        slice_index : int = None
        try: slice_index = int(slice)
        except: pass
        if slice_index is not None and slice_index < 0: return f"{source}.slice({slice})"
        else: return f"{source}[{slice}]"
    
    def _translate_unary_op(self, expression: UnaryOp) -> str:
        operand = self.translate(expression.operand)
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