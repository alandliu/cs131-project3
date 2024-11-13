from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from data_object import Data_Object
from struct_object import Struct_Object


# returns of any kind must be a data object
class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output

    def get_main_func_node(self, ast):
        if ast.elem_type == self.PROGRAM_NODE:
            for f in ast.dict['functions']:
                func_name = f.dict['name'] + '_' + str(len(f.dict['args']))
                self.func_defs_to_node[func_name] = f
        if 'main_0' in self.func_defs_to_node:
            return self.func_defs_to_node['main_0']
        super().error(
            ErrorType.NAME_ERROR,
            "No main() function was found"
        )

    def run(self, program):
        self.ast = parse_program(program)
        if self.trace_output:
            print(self.ast)
        self.var_name_to_val = dict()
        self.func_defs_to_node = dict()
        self.global_scope = [ self.var_name_to_val ]
        self.val_types = [ self.INT_NODE, self.BOOL_NODE, self.STRING_NODE, self.NIL_NODE ]
        self.struct_types = [s.dict['name'] for s in self.ast.dict['structs']]
        self.arithmetic_ops = ['+', '-', '*', '/', self.NEG_NODE]
        self.comparison_ops = ['<', '>', '<=', '>=', '==', '!=']
        self.bool_ops = ['&&', '||', '!']
        main_func_node = self.get_main_func_node(self.ast)
        self.run_func(main_func_node, self.global_scope)
    
    def run_func(self, func_node, scopes):
        if self.trace_output:
            print("Running function: " + func_node.dict['name'])
            print(scopes)
        for statement in func_node.dict['statements']:
            ret = self.run_statement(statement, scopes)
            if ret or statement.elem_type == self.RETURN_NODE:
                return
        return
    
    def run_statement(self, statement_node, scopes):
        if self.trace_output:
            print('Running statement: ' + statement_node.elem_type)
            print(scopes)
        elem_type = statement_node.elem_type
        ret = False
        if elem_type == self.VAR_DEF_NODE:
            self.do_definition(statement_node, scopes)
        elif elem_type == '=':
            self.do_assignment(statement_node, scopes)
        elif elem_type == self.FCALL_NODE:
            self.do_call(statement_node, scopes)
        elif elem_type == self.IF_NODE:
            ret = self.do_if(statement_node, scopes)
        elif elem_type == self.FOR_NODE:
            ret = self.do_for(statement_node, scopes)
        elif elem_type == self.RETURN_NODE:
            ret = self.do_return(statement_node, scopes)
        return ret
    
    def run_body(self, statements, scopes):
        if statements == None:
            return False
        for statement in statements:
            ret = self.run_statement(statement, scopes)
            if ret or statement.elem_type == self.RETURN_NODE:
                return True
        return False

    #####################################################################
    # statement behaviors
    #####################################################################
    
    def do_definition(self, statement_node, scopes):
        if self.trace_output:
            print("Running definition: " + statement_node.dict['name'])
            print(scopes)
        local_scope = scopes[-1]
        var_name = statement_node.dict['name']
        if var_name in local_scope:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} defined more than once",
            )
        local_scope[statement_node.dict['name']] = self.nil_object()
        return
    
    def do_assignment(self, statement_node, scopes):
        if self.trace_output:
            print("Running assignment: " + statement_node.dict['name'])
            print(scopes)
        ref_scope = None
        var_name = statement_node.dict['name']
        for scope in reversed(scopes):
            if var_name in scope:
                ref_scope = scope
                break
        if ref_scope == None:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} has not been defined",
            )

        expression = statement_node.dict['expression']
        result = self.nil_object()
        if expression.elem_type in self.val_types:
            result = self.evaluate_value(expression, scopes)
        elif expression.elem_type == self.VAR_NODE:
            result = self.evaluate_variable_node(expression, scopes)
        elif expression.elem_type == self.FCALL_NODE:
            result = self.do_call(expression, scopes)
        elif expression.elem_type == self.NIL_NODE:
            result = self.nil_object()
        else:
            result = self.evaluate_expression(expression, scopes)
            
        # Returns will ALWAYS be Data Objects
        ref_scope[var_name] = result
        return
    
    def do_call(self, statement_node, scopes):
        if self.trace_output:
            print('Running call: ' + statement_node.dict['name'])
            print(scopes)
        fcall_name = statement_node.dict['name']

        if fcall_name == 'print':
            return self.fcall_print(statement_node.dict['args'], scopes)

        elif fcall_name == 'inputi':
            return self.fcall_inputi(scopes, statement_node.dict['args'])
        elif fcall_name == 'inputs':
            return self.fcall_inputs(scopes, statement_node.dict['args'])
        
        fcall_dict_key = fcall_name + '_' + str(len(statement_node.dict['args']))
        if fcall_dict_key not in self.func_defs_to_node:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {fcall_name} was not found",
            )
        new_scope = dict()
        new_scope['ret'] = Data_Object(self.NIL_NODE, None)
        fcall_arg_name_list = self.func_defs_to_node[fcall_dict_key].dict['args']
        fcall_arg_list = statement_node.dict['args']
        for i in range(len(fcall_arg_list)):
            cur_arg_node = fcall_arg_list[i]
            arg = None
            if cur_arg_node.elem_type == self.VAR_NODE:
                arg = self.evaluate_variable_node(cur_arg_node, scopes)
            elif cur_arg_node.elem_type in self.val_types:
                arg = self.evaluate_value(cur_arg_node, scopes)
            elif cur_arg_node.elem_type == self.FCALL_NODE:
                arg = self.do_call(cur_arg_node, scopes)
            else:
                arg = self.evaluate_expression(cur_arg_node, scopes)
            new_scope[fcall_arg_name_list[i].dict['name']] = arg
        func_context = [new_scope, dict()]
        self.run_func(self.func_defs_to_node[fcall_dict_key], func_context)
        return func_context[0]['ret']
    
    def do_if(self, if_node, scopes):
        if self.trace_output:
            print("Running if node")
            print(scopes)
        condition_node = if_node.dict['condition']
        condition_result = self.evaluate_conditional(condition_node, scopes)
        new_scopes = scopes + [dict()]
        if condition_result.get_value(): 
            ret = self.run_body(if_node.dict['statements'], new_scopes)
        else:
            ret = self.run_body(if_node.dict['else_statements'], new_scopes)

        if ret:
            return True
        return False
    
    def do_for(self, for_node, scopes):
        if self.trace_output:
            print("Running for_loop")
            print(scopes)
        self.do_assignment(for_node.dict['init'], scopes)
        condition_node = for_node.dict['condition']
        condition_eval = self.evaluate_conditional(condition_node, scopes)
        while condition_eval.get_value():
            new_scope = scopes + [dict()]
            ret = self.run_body(for_node.dict['statements'], new_scope)
            if ret:
                return True
            self.do_assignment(for_node.dict['update'], scopes)
            condition_eval = self.evaluate_conditional(condition_node, scopes)
        return False
    
    def do_return(self, return_node, scopes):
        if self.trace_output:
            print("Running return")
            print(scopes)
        ret_val = None
        if return_node.dict['expression'] == None:
            return True
        
        ret_eval_type = return_node.dict['expression'].elem_type
        if ret_eval_type == self.VAR_NODE:
            ret_val = self.evaluate_variable_node(return_node.dict['expression'], scopes)
        elif ret_eval_type in self.val_types:
            ret_val = self.evaluate_value(return_node.dict['expression'], scopes)
        elif ret_eval_type in self.bool_ops or ret_eval_type in self.arithmetic_ops or ret_eval_type in self.comparison_ops:
            ret_val = self.evaluate_expression(return_node.dict['expression'], scopes)
        elif ret_eval_type == self.FCALL_NODE:
            ret_val = self.do_call(return_node.dict['expression'], scopes)
        scopes[0]['ret'] = ret_val
        return True

    #####################################################################
    # expression node evaluation 
    #####################################################################
    
    def evaluate_expression(self, expression_node, scopes):
        if self.trace_output:
            print("Running evaluation: " + expression_node.elem_type)
            print(scopes)
        elem_type = expression_node.elem_type
        elem_1 = expression_node.dict['op1']
        operand_1 = self.evaluate_operand(elem_1, scopes)

        if elem_type == self.NEG_NODE:
            if operand_1.get_type() != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible type for neg operation"
                )
            return Data_Object(self.INT_NODE, -1 * operand_1.get_value())
        elif elem_type == self.NOT_NODE:
            if operand_1.get_type() != self.BOOL_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible type for ! operation"
                )
            return Data_Object(self.BOOL_NODE, not operand_1.get_value())
        
        elem_2 = expression_node.dict['op2']
        operand_2 = self.evaluate_operand(elem_2, scopes)

        if elem_type == '+':
            if self.check_addition_compatible(operand_1, operand_2):
                result = operand_1 + operand_2
                if type(result) is int:
                    return Data_Object(self.INT_NODE, result)
                return Data_Object(self.STRING_NODE, result)
            super().error(
                ErrorType.TYPE_ERROR,
                f"Cannot use operator + on non-string and non-integer operators"
            )
        elif elem_type == '-':
            if operand_1.get_type() != self.INT_NODE or operand_2.get_type() != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot use operator - on non-integer operators"
                )
            return Data_Object(self.INT_NODE, operand_1 - operand_2)
        elif elem_type == '/':
            if operand_1.get_type() != self.INT_NODE or operand_2.get_type() != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot use operator / on non-integer operators"
                )
            return Data_Object(self.INT_NODE, operand_1 // operand_2)
        elif elem_type == '*':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return Data_Object(self.INT_NODE, operand_1 * operand_2)
        elif elem_type == '==':
            if operand_1.get_type() != operand_2.get_type():
                return self.false_object()
            return Data_Object(self.BOOL_NODE, operand_1 == operand_2)
        elif elem_type == '<':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return Data_Object(self.BOOL_NODE, operand_1 < operand_2)
        elif elem_type == '>':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return Data_Object(self.BOOL_NODE, operand_1 > operand_2)
        elif elem_type == '<=':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return Data_Object(self.BOOL_NODE, operand_1 <= operand_2)
        elif elem_type == '>=':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return Data_Object(self.BOOL_NODE, operand_1 >= operand_2)
        elif elem_type == '!=':
            if operand_1.get_type() != operand_2.get_type():
                return self.true_object()
            return Data_Object(self.BOOL_NODE, operand_1 != operand_2)
        elif elem_type == '||':
            if operand_1.get_type() != self.BOOL_NODE or operand_2.get_type() != self.BOOL_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot use operator || on non-boolean operators"
                )
            return Data_Object(self.BOOL_NODE, operand_1.get_value() or operand_2.get_value())
        elif elem_type == '&&':
            if operand_1.get_type() != self.BOOL_NODE or operand_2.get_type() != self.BOOL_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot use operator && on non-boolean operators"
                )
            return Data_Object(self.BOOL_NODE, operand_1.get_value() and operand_2.get_value())

    #####################################################################
    # variable node evaluation 
    #####################################################################
    
    def evaluate_variable_node(self, var_node, scopes):
        if self.trace_output:
            print("Running retrieval: " + var_node.dict['name'])
            print(scopes)
        var_name = var_node.dict['name']
        for scope in reversed(scopes):
            if var_name in scope:
                return scope[var_name]
        super().error(
            ErrorType.NAME_ERROR,
            f"Variable {var_name} has not been defined",
        )

    #####################################################################
    # value node evaluation 
    #####################################################################
    
    def evaluate_value(self, val_node, scopes):
        if self.trace_output:
            print("Running constant_type: " + val_node.elem_type)
            print(scopes)
        if val_node.elem_type == self.BOOL_NODE:
            if val_node.dict['val'] == self.TRUE_DEF:
                return self.true_object()
            elif val_node.dict['val'] == self.FALSE_DEF:
                return self.false_object()
        elif val_node.elem_type == self.NIL_NODE:
            return self.nil_object()
        return Data_Object(val_node.elem_type, val_node.dict['val'])

    #####################################################################
    # operand node evaluation 
    #####################################################################
    
    def evaluate_operand(self, operand_node, scopes):
        if operand_node.elem_type == self.VAR_NODE:
            return self.evaluate_variable_node(operand_node, scopes)
        elif operand_node.elem_type in self.arithmetic_ops or operand_node.elem_type in self.bool_ops or operand_node.elem_type in self.comparison_ops:
            return self.evaluate_expression(operand_node, scopes)
        elif operand_node.elem_type == self.FCALL_NODE:
            return self.do_call(operand_node, scopes)
        elif operand_node.elem_type == self.NIL_NODE:
            return self.nil_object()
        else:
            return self.evaluate_value(operand_node, scopes)


    #####################################################################
    # conditional (for/if) node evalution
    #####################################################################
    
    def evaluate_conditional(self, condition_node, scopes):
        condition_type = condition_node.elem_type
        condition_eval = self.nil_object()
        if condition_type == self.VAR_NODE:
            condition_eval = self.evaluate_variable_node(condition_node, scopes)
        elif condition_type == self.BOOL_NODE:
            condition_eval = self.evaluate_value(condition_node, scopes)
        elif condition_type in self.bool_ops or condition_type in self.comparison_ops:
            condition_eval = self.evaluate_expression(condition_node, scopes)

        if not self.check_boolean(condition_eval):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Expression does not evaluate to boolean",
            )
        return condition_eval

    #####################################################################
    # custom functions (called from any scope)
    #####################################################################

    def fcall_print(self, args, scopes):
        if self.trace_output:
            print("Running print")
            print(scopes)
        output = ""
        for arg in args:
            if arg.elem_type == self.VAR_NODE:
                res = self.evaluate_variable_node(arg, scopes)
                if res.get_type() == self.BOOL_NODE:
                    output += self.fcall_print_bool_helper(res)
                else:
                    output += str(res.get_value())
            elif arg.elem_type == self.INT_NODE or arg.elem_type == self.STRING_NODE:
                output += str(self.evaluate_value(arg, scopes).get_value())
            elif arg.elem_type in self.arithmetic_ops:
                output += str(self.evaluate_expression(arg, scopes).get_value())
            elif arg.elem_type in self.comparison_ops or arg.elem_type in self.bool_ops:
                res = self.evaluate_expression(arg, scopes)
                output += self.fcall_print_bool_helper(res)
            elif arg.elem_type == self.BOOL_NODE:
                output += self.fcall_print_bool_helper(Data_Object(self.BOOL_NODE, arg.dict['val']))
            elif arg.elem_type == self.FCALL_NODE:
                res = self.do_call(arg, scopes)
                if res.get_type() == self.BOOL_NODE:
                    output += self.fcall_print_bool_helper(res)
                else:
                    output += str(res.get_value())
        super().output(output)
        return self.nil_object()
    
    def fcall_inputi(self, scopes, prompt = None):
        if self.trace_output:
            print("Running inputi")
        if prompt is None:
            prompt = ""
        elif len(prompt) > 2:
            super().error(
                ErrorType.NAME_ERROR,
                f"No inputi() function found that takes > 1 parameter",
            )
        elif len(prompt) > 0:
            super().output(self.evaluate_value(prompt[0], scopes).get_value())
        return Data_Object(self.INT_NODE, int(super().get_input()))

    def fcall_inputs(self, scopes, prompt = None):
        if self.trace_output:
            print("Running inputs")
        if prompt is None:
            prompt = ""
        elif len(prompt) > 2:
            super().error(
                ErrorType.NAME_ERROR,
                f"No inputs() function found that takes > 1 parameter",
            )
        elif len(prompt) > 0:
            super().output(self.evaluate_value(prompt[0], scopes).get_value())
        return Data_Object(self.STRING_NODE, str(super().get_input()))


    #####################################################################
    #  Util and Abstracted helpers
    #####################################################################
    def check_boolean(self, condition):
        return condition.get_type() == self.BOOL_NODE

    def fcall_print_bool_helper(self, val):
        if val.get_value():
            return 'true'
        return 'false'

    def verify_integer(self, condition, elem_type):
        if condition.get_type() != self.INT_NODE:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {elem_type} operation",
            )

    def type_check(self, op_1, op_2, elem_type):
        if op_1.get_type() != op_2.get_type():
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {elem_type} operation",
            )

    def check_addition_compatible(self, op_1, op_2):
        if op_1.get_type() != self.STRING_NODE and op_1.get_type() != self.INT_NODE:
            return False
        if op_2.get_type() != self.STRING_NODE and op_2.get_type() != self.INT_NODE:
            return False
        return True

    #####################################################################
    #  Constant Data Nodes
    #####################################################################
    def nil_object(self):
        return Data_Object(self.NIL_NODE, None)
    
    def true_object(self):
        return Data_Object(self.BOOL_NODE, True)
    
    def false_object(self):
        return Data_Object(self.BOOL_NODE, False)
    
    
