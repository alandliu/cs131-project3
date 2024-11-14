from data_object import Data_Object

class Struct_Object(Data_Object):
    def __init__(self, struct_node):
        super().__init__()

    def __eq__(self, other):
        return self is other