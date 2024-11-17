from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from data_object import Data_Object
from struct_object import Struct_Object


# returns of any kind must be a data object
class Interpreter(InterpreterBase):
    
    #####################################################################
    # Init functions
    #####################################################################
    
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

    def verify_all_func_types(self):
        for func_key in self.func_defs_to_node.keys():
            cur_func_node = self.func_defs_to_node[func_key]
            func_ret_type = cur_func_node.dict['return_type']
            if func_ret_type not in self.var_types and func_ret_type not in self.struct_types and func_ret_type != self.VOID_DEF:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid return type {func_ret_type} in function {cur_func_node.dict['name']}"
                )

    def verify_all_struct_fields(self):
        for struct_key in self.struct_types.keys():
            struct_fields = self.struct_types[struct_key]
            for field in struct_fields:
                field_type = field.dict['var_type']
                if field_type not in self.var_types and field_type not in self.struct_types:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Invalid type when defining struct {struct_key}"
                    )

    def run(self, program):
        self.ast = parse_program(program)
        if self.trace_output:
            print(self.ast)

        self.var_name_to_val = dict()
        self.func_defs_to_node = dict()
        self.valid_coercions = { self.INT_NODE: [self.BOOL_NODE] }
        self.struct_types = {s.dict['name'] : s.dict['fields'] for s in self.ast.dict['structs']}

        self.global_scope = [ self.var_name_to_val ]
        self.var_types = [ self.INT_NODE, self.BOOL_NODE, self.STRING_NODE, self.NIL_NODE ]
        self.arithmetic_ops = ['+', '-', '*', '/', self.NEG_NODE]
        self.comparison_ops = ['<', '>', '<=', '>=', '==', '!=']
        self.bool_ops = ['&&', '||', '!']

        main_func_node = self.get_main_func_node(self.ast)
        self.verify_all_func_types()
        self.verify_all_struct_fields()

        self.run_func(main_func_node, self.global_scope)

    #####################################################################
    # body execution functions
    #####################################################################
    
    def run_func(self, func_node, scopes):
        if self.trace_output:
            print("Running function: " + func_node.dict['name'])
            print(scopes)
        for statement in func_node.dict['statements']:
            ret = self.run_statement(statement, scopes)
            if ret or statement.elem_type == self.RETURN_NODE:
                return
        return
    
    def run_body(self, statements, scopes):
        if statements == None:
            return False
        for statement in statements:
            ret = self.run_statement(statement, scopes)
            if ret or statement.elem_type == self.RETURN_NODE:
                return True
        return False
    
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

        var_type = statement_node.dict['var_type']
        init_val = self.nil_object()
        if var_type == self.INT_NODE:
            init_val = self.int_object()
        elif var_type == self.STRING_NODE:
            init_val = self.string_object()
        elif var_type == self.BOOL_NODE:
            init_val = self.false_object()
        elif var_type in self.struct_types:
            init_val = self.nil_object(var_type)
        else:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Unknown/invalid type specified {var_type}"
            )
        local_scope[var_name] = init_val
        return
    
    def do_assignment(self, statement_node, scopes):
        if self.trace_output:
            print("Running assignment: " + statement_node.dict['name'])
            print(scopes)
        ref_scope = None
        var_segments = statement_node.dict['name'].split('.')
        var_name = var_segments[0]
        var_fields = var_segments[1:]
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
        if expression.elem_type in self.var_types:
            result = self.evaluate_value(expression, scopes)
        elif expression.elem_type == self.VAR_NODE:
            result = self.evaluate_variable_node(expression, scopes)
        elif expression.elem_type == self.FCALL_NODE:
            result = self.do_call(expression, scopes)
        elif expression.elem_type == self.NIL_NODE:
            result = self.nil_object()
        else:
            result = self.evaluate_expression(expression, scopes)
            
        var_type = ref_scope[var_name].get_type()
        assign_type = result.get_type()

        self.check_struct_equivalence(ref_scope[var_name], result)

        if len(var_fields) > 0:
            res_struct, field_name = self.get_struct_member(ref_scope[var_name], var_fields, statement_node.dict['name'])
            var_type = res_struct.get_field_type(field_name)
            result = self.assign_helper(var_type, assign_type, res_struct.get_field(field_name), result)
            res_struct.change_field(field_name, result)
            return 
        result = self.assign_helper(var_type, assign_type, ref_scope[var_name], result)
        ref_scope[var_name] = result
        return
    
    def check_struct_equivalence(self, obj_1, obj_2):
        if obj_1.get_type() == self.NIL_NODE and obj_2.get_type() == self.NIL_NODE:
            if obj_1.struct_type != self.NIL_NODE and obj_2.struct_type != self.NIL_NODE:
                if obj_1.struct_type != obj_2.struct_type:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Type mismatch {obj_1.struct_type} vs {obj_2.struct_type}"
                    )

    def assign_helper(self, var_type, assign_type, ref_struct, result):
        if var_type == assign_type:
            return result
        elif var_type == self.BOOL_NODE and assign_type == self.INT_NODE:
            return result.coerce_i_to_b()
        elif var_type == self.NIL_DEF and assign_type in self.struct_types and ref_struct.struct_type == assign_type:
            return result
        elif var_type in self.struct_types and assign_type == self.NIL_NODE:
            return self.nil_object(var_type)
        else:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Type mismatch {var_type} vs {assign_type} in assignment"
            )
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
        default_return = self.void_object()
        return_type = self.func_defs_to_node[fcall_dict_key].dict['return_type']
        if return_type == self.INT_NODE:
            default_return = self.int_object()
        elif return_type == self.BOOL_NODE:
            default_return = self.false_object()
        elif return_type == self.STRING_NODE:
            default_return = self.string_object()
        elif return_type in self.struct_types:
            default_return = self.nil_object()

        new_scope['ret'] = default_return
        fcall_arg_param_list = self.func_defs_to_node[fcall_dict_key].dict['args']
        fcall_arg_list = statement_node.dict['args']
        for i in range(len(fcall_arg_list)):
            cur_arg_node = fcall_arg_list[i]
            cur_param_name = fcall_arg_param_list[i].dict['name']
            cur_param_type = fcall_arg_param_list[i].dict['var_type']
            arg = None
            if cur_arg_node.elem_type == self.VAR_NODE:
                arg = self.evaluate_variable_node(cur_arg_node, scopes)
            elif cur_arg_node.elem_type in self.var_types:
                arg = self.evaluate_value(cur_arg_node, scopes)
            elif cur_arg_node.elem_type == self.FCALL_NODE:
                arg = self.do_call(cur_arg_node, scopes)
            else:
                arg = self.evaluate_expression(cur_arg_node, scopes)

            if cur_param_type != arg.get_type():
                if cur_param_type == self.BOOL_NODE and arg.get_type() == self.INT_NODE:
                    arg = arg.coerce_i_to_b()
                elif cur_param_type in self.struct_types and arg.get_type() == self.NIL_NODE and arg.struct_type == cur_param_type:
                    arg = arg
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Type mismatch on formal parameter {cur_param_name}"
                    )
            new_scope[cur_param_name] = arg
        func_context = [new_scope, dict()]
        self.run_func(self.func_defs_to_node[fcall_dict_key], func_context)

        func_return = func_context[0]['ret']
        if func_return.get_type() != return_type:
            if func_return.get_type() == self.INT_NODE and return_type == self.BOOL_NODE:
                func_return = func_return.coerce_i_to_b()
            elif func_return.get_type() == self.NIL_NODE and return_type in self.struct_types:
                func_return = self.nil_object()
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Returned value's type {func_return.get_type()} is inconsistent with function's return type {return_type}"
                )
        return func_return
    
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
        elif ret_eval_type in self.var_types:
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
        if elem_type == self.NEW_NODE:
            struct_name = expression_node.dict['var_type']
            if struct_name not in self.struct_types:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid type {struct_name} for new operation"
                )
            return self.init_new_struct(struct_name)

        elem_1 = expression_node.dict['op1']
        operand_1 = self.evaluate_operand(elem_1, scopes)
        op1_type = operand_1.get_type()

        if elem_type == self.NEG_NODE:
            if op1_type != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible type for neg operation"
                )
            return -operand_1
        elif elem_type == self.NOT_NODE:
            if op1_type != self.BOOL_NODE and op1_type != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible type for ! operation"
                )
            return not operand_1
        
        elem_2 = expression_node.dict['op2']
        operand_2 = self.evaluate_operand(elem_2, scopes)
        op2_type = operand_2.get_type()

        self.check_struct_equivalence(operand_1, operand_2)

        if op1_type == self.VOID_DEF or op2_type == self.VOID_DEF:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Can't compare void type"
            )

        if elem_type == '+':
            if self.check_addition_compatible(operand_1, operand_2):
                return operand_1 + operand_2
            super().error(
                ErrorType.TYPE_ERROR,
                f"Cannot use operator + on non-string and non-integer operators"
            )
        elif elem_type == '-':
            if op1_type != self.INT_NODE or op2_type != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot use operator - on non-integer operators"
                )
            return operand_1 - operand_2
        elif elem_type == '/':
            if op1_type != self.INT_NODE or op2_type != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot use operator / on non-integer operators"
                )
            return operand_1 // operand_2
        elif elem_type == '*':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return operand_1 * operand_2
        elif elem_type == '==':
            if op1_type != op2_type:
                if (op1_type == self.INT_NODE or op1_type == self.BOOL_NODE) and (op2_type == self.INT_NODE or op2_type == self.BOOL_NODE):
                    operand_1 = operand_1.coerce_i_to_b()
                    operand_2 = operand_2.coerce_i_to_b()
                elif op1_type in self.struct_types and op2_type == self.NIL_NODE or op1_type == self.NIL_NODE and op2_type in self.struct_types:
                    return operand_1 == operand_2
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Can't compare unrelated types {op1_type} and {op2_type}"
                    )
            return operand_1 == operand_2
        elif elem_type == '<':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return operand_1 < operand_2
        elif elem_type == '>':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return operand_1 > operand_2
        elif elem_type == '<=':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return operand_1 <= operand_2
        elif elem_type == '>=':
            self.type_check(operand_1, operand_2, elem_type)
            self.verify_integer(operand_1, elem_type)
            return operand_1 >= operand_2
        elif elem_type == '!=':
            if op1_type != op2_type:
                if (op1_type == self.INT_NODE or op1_type == self.BOOL_NODE) and (op2_type == self.INT_NODE or op2_type == self.BOOL_NODE):
                    operand_1 = operand_1.coerce_i_to_b()
                    operand_2 = operand_2.coerce_i_to_b()
                elif op1_type in self.struct_types and op2_type == self.NIL_NODE or op1_type == self.NIL_NODE and op2_type in self.struct_types:
                    return operand_1 != operand_2
                else:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Can't compare unrelated types {op1_type} and {op2_type}"
                    )
            return operand_1 != operand_2
        elif elem_type == '||':
            if op1_type != self.BOOL_NODE and op1_type != self.INT_NODE or op2_type != self.BOOL_NODE and op2_type != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid types used with operator ||"
                )
            return operand_1.logical_or(operand_2)
        elif elem_type == '&&':
            if op1_type != self.BOOL_NODE and op1_type != self.INT_NODE or op2_type != self.BOOL_NODE and op2_type != self.INT_NODE:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid types used with operator &&"
                )
            return operand_1.logical_and(operand_2)

    def init_new_struct(self, struct_type):
        return Struct_Object(struct_type, struct_type, self.struct_types[struct_type])

    #####################################################################
    # variable node evaluation 
    #####################################################################
    
    def evaluate_variable_node(self, var_node, scopes):
        if self.trace_output:
            print("Running retrieval: " + var_node.dict['name'])
            print(scopes)
        var_segments = var_node.dict['name'].split('.')
        var_name = var_segments[0]
        var_fields = var_segments[1:]
        for scope in reversed(scopes):
            if var_name in scope:
                if len(var_fields) == 0:
                    return scope[var_name]
                res_struct, field_name = self.get_struct_member(scope[var_name], var_fields, var_node.dict['name'])
                return res_struct.get_field(field_name)
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
        condition_eval = self.false_object()
        if condition_type == self.VAR_NODE:
            condition_eval = self.evaluate_variable_node(condition_node, scopes)
        elif condition_type == self.BOOL_NODE or condition_type == self.INT_NODE:
            condition_eval = self.evaluate_value(condition_node, scopes)
        elif condition_type in self.bool_ops or condition_type in self.comparison_ops or condition_type in self.arithmetic_ops:
            condition_eval = self.evaluate_expression(condition_node, scopes)
        elif condition_type == self.FCALL_NODE:
            condition_eval = self.do_call(condition_node, scopes)
       
        if condition_eval.get_type() == self.INT_NODE:
            condition_eval = condition_eval.coerce_i_to_b()

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
            res = None
            if arg.elem_type == self.VAR_NODE:
                res = self.evaluate_variable_node(arg, scopes)
                if res.get_type() == self.BOOL_NODE:
                    res = self.fcall_print_bool_helper(res)
                elif res.get_type() == self.NIL_NODE:
                    res = self.NIL_DEF
                else:
                    res = str(res.get_value())
            elif arg.elem_type == self.INT_NODE or arg.elem_type == self.STRING_NODE:
                res = str(self.evaluate_value(arg, scopes).get_value())
            elif arg.elem_type in self.arithmetic_ops:
                res = str(self.evaluate_expression(arg, scopes).get_value())
            elif arg.elem_type in self.comparison_ops or arg.elem_type in self.bool_ops:
                res = self.evaluate_expression(arg, scopes)
                res = self.fcall_print_bool_helper(res)
            elif arg.elem_type == self.BOOL_NODE:
                res = self.fcall_print_bool_helper(Data_Object(self.BOOL_NODE, arg.dict['val']))
            elif arg.elem_type == self.FCALL_NODE:
                res = self.do_call(arg, scopes)
                if res.get_type() == self.BOOL_NODE:
                    res = self.fcall_print_bool_helper(res)
                elif res.get_type() == self.NIL_NODE:
                    res = self.NIL_DEF
                elif res.get_type() == self.VOID_DEF:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Cannot print type void"
                    )
                else:
                    res = str(res.get_value())
            elif arg.elem_type == self.NIL_NODE:
                res = self.NIL_DEF

            if res == None:
                res = self.NIL_DEF

            output += res
        super().output(output)
        return self.void_object()
    
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
    def nil_object(self, struct_type = 'nil'):
        return Struct_Object(self.NIL_NODE, struct_type, [])
    
    def void_object(self):
        return Data_Object.void_object(self.VOID_DEF)
    
    def true_object(self):
        return Data_Object.true_object(self.BOOL_NODE)
    
    def false_object(self):
        return Data_Object.false_object(self.BOOL_NODE)
    
    def int_object(self):
        return Data_Object.int_object(self.INT_NODE)
    
    def string_object(self):
        return Data_Object.string_object(self.STRING_NODE)
    
    #####################################################################
    #  Struct Helpers
    #####################################################################
    
    def get_struct_member(self, ref_struct, var_fields, full_name):
        self.verify_dot_operation(ref_struct.get_type(), var_fields[0], full_name)
        if len(var_fields) == 1:
            return ref_struct, var_fields[0]
        n_ref_struct = ref_struct.get_field(var_fields[0])
        n_var_fields = var_fields[1:]
        return self.get_struct_member(n_ref_struct, n_var_fields, full_name)
    
    def verify_dot_operation(self, var_type, var_name, full_name):
        if var_type == self.NIL_NODE:
            super().error(
                ErrorType.FAULT_ERROR,
                f"Error dereferencing nil value {var_name} in {full_name}"
            )
        elif var_type not in self.struct_types:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Dot used with non-struct {var_type} in {full_name}"
            )
        return
    