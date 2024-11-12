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