import methodtools as mt
import time

class testClass:
    
    def __init__ (self):
        self.value = 0
        self.dependent_value = 0
    
    @mt.lru_cache()
    @staticmethod
    def _compute_property(dependent_value):
        time.sleep(4)  # Simulate a time-consuming computation
        return dependent_value
    
    @property
    def my_property(self):
        return self._compute_property(self.dependent_value)
    
    def set_value(self, new_value):
        self.value = new_value

    def set_dependent_value(self, new_value):
        self.dependent_value = new_value

mytestClass = testClass()
print(mytestClass.my_property)  # First call, takes time
print(mytestClass.my_property)  # Second call, returns cached result
mytestClass.set_value(10)
print(mytestClass.my_property)  # Still returns cached result
mytestClass.set_dependent_value(5)
print(mytestClass.my_property)  # New dependent value, takes time again
print(mytestClass.my_property)  # New dependent value, returns cached result
