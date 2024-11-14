from data_object import Data_Object

class Struct_Object(Data_Object):
    def __init__(self, init_type, struct_type, field_nodes):
        super().__init__(init_type, None)
        self.struct_type = struct_type
        self.fields = dict()
        for field in field_nodes:
            field_name = field.dict['name']
            field_type = field.dict['var_type']
            if field_type == self.INT_TYPE:
                self.fields[field_name] = self.int_object(self.INT_TYPE)
            elif field_type == self.BOOL_TYPE:
                self.fields[field_name] = self.false_object(self.BOOL_TYPE)
            elif field_type == self.STRING_TYPE:
                self.fields[field_name] = self.string_object(self.STRING_TYPE)
            else:
                self.fields[field_name] = self.nil_object(self.NIL_TYPE)

    def __str__(self):
        return f"Struct {self.struct_type}"

    def __repr__(self):
        res = f"({self.val_type} {self.struct_type} "
        for f_name in self.fields.keys():
            res += f_name + ":"
            f_val = self.fields[f_name]
            res += str(f_val)
            res += ", "
        res += ")"
        return res

    def __eq__(self, other):
        return self is other
    
    
    def change_field(self, field_name, field_data):
        self.fields[field_name] = field_data
    
    def get_field(self, field_name):
        return self.fields[field_name]
    
    def get_field_type(self, field_name):
        return self.get_field(field_name).get_type()
    
    