
class Data_Object:
    INT_TYPE = 'int'
    STRING_TYPE = 'string'
    BOOL_TYPE = 'bool'
    VOID_TYPE = 'void'
    NIL_TYPE = 'nil'
    COERCIBLE = [ INT_TYPE, BOOL_TYPE ]

    def __init__(self, val_type, value):
        self.val_type = val_type
        self.value = value

    def get_type(self):
        return self.val_type
    
    def get_value(self):
        return self.value
    
    def set_value(self, val):
        self.value = val

    # Representation and Coercion
    def __str__(self):
        return f"{self.value}"
    
    def __repr__(self):
        return f"(type={self.val_type},val={self.value})"

    def coerce_i_to_b(self):
        if self.val_type == self.BOOL_TYPE:
            return self
        return Data_Object(self.BOOL_TYPE, self.value != 0)
    
    # ARITHMETIC
    def __add__(self, other):
        if other.val_type == self.STRING_TYPE or self.val_type == self.STRING_TYPE:
            return Data_Object(self.STRING_TYPE, str(self.value) + str(other.value))
        return Data_Object(self.INT_TYPE, self.value + other.value)
    
    def __sub__(self, other):
        return Data_Object(self.INT_TYPE, self.value - other.value)
    
    def __floordiv__(self, other):
        return Data_Object(self.INT_TYPE, self.value // other.value)
    
    def __mul__(self, other):
        return Data_Object(self.INT_TYPE, self.value * other.value)
    
    def __neg__(self):
        return Data_Object(self.INT_TYPE, -1 * self.value)
    
    
    # COMPARISON
    def __gt__(self, other):
        return Data_Object(self.BOOL_TYPE, self.value > other.value)
    
    def __lt__(self, other):
        return Data_Object(self.BOOL_TYPE, self.value < other.value)
    
    def __eq__(self, other):
        return Data_Object(self.BOOL_TYPE, self.value == other.value)
    
    def __le__(self, other):
        return Data_Object(self.BOOL_TYPE, self.value <= other.value)
    
    def __ge__(self, other):
        return Data_Object(self.BOOL_TYPE, self.value >= other.value)
    
    def __ne__(self, other):
        return Data_Object(self.BOOL_TYPE, self.value != other.value)
    
    def __not__(self):
        return Data_Object(self.BOOL_TYPE, not self.value)
    
    # BOOLEAN
    def logical_and(self, other):
        res = self.coerce_i_to_b().get_value() and other.coerce_i_to_b().get_value()
        return Data_Object(self.BOOL_TYPE, res)
    
    def logical_or(self, other):
        res = self.coerce_i_to_b().get_value() or other.coerce_i_to_b().get_value()
        return Data_Object(self.BOOL_TYPE, res)
    
    # DEFAULTS
    @staticmethod
    def void_object(VOID_TYPE):
        return Data_Object(VOID_TYPE, None)
    
    @staticmethod
    def true_object(BOOL_TYPE):
        return Data_Object(BOOL_TYPE, True)
    
    @staticmethod
    def false_object(BOOL_TYPE):
        return Data_Object(BOOL_TYPE, False)
    
    @staticmethod
    def int_object(INT_TYPE):
        return Data_Object(INT_TYPE, 0)
    
    @staticmethod
    def string_object(STRING_TYPE):
        return Data_Object(STRING_TYPE, "")