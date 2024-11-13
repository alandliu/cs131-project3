class Data_Object:
    def __init__(self, val_type, value):
        self.val_type = val_type
        self.value = value

    def get_type(self):
        return self.val_type
    
    def get_value(self):
        return self.value
    
    def set_value(self, val):
        self.value = val

    # Representation

    def __str__(self):
        return f"{self.value}"
    
    def __repr__(self):
        return f"(type={self.val_type},val={self.value})"
    
    # ARITHMETIC
    def __add__(self, other):
        return self.value + other.value
    
    def __sub__(self, other):
        return self.value - other.value
    
    def __floordiv__(self, other):
        return self.value // other.value
    
    def __mul__(self, other):
        return self.value * other.value
    
    
    # COMPARISON
    def __gt__(self, other):
        return self.value > other.value
    
    def __lt__(self, other):
        return self.value < other.value
    
    def __eq__(self, other):
        return self.value == other.value
    
    def __le__(self, other):
        return self.value <= other.value
    
    def __ge__(self, other):
        return self.value >= other.value
    
    def __ne__(self, other):
        return self.value != other.value