# Adapted from http://code.activestate.com/recipes/67107/

import types
import string
import pprint
import exceptions

class EnumException(exceptions.Exception):
    pass

class EnumValue:
    def __init__(self, id, name):
        self.id = id
        self.name = name
            
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return "%d|%s" % (self.id, self.name)
    
class Enumeration:
    def __init__(self, name, enumList):
        self.__doc__ = name
        lookup = { }
        reverseLookup = { }
        i = 0
        uniqueNames = [ ]
        uniqueValues = [ ]
        for x in enumList:
            if type(x) == types.TupleType:
                x, i = x
            if type(x) != types.StringType:
                raise EnumException, "enum name is not a string: " + x
            if type(i) != types.IntType:
                raise EnumException, "enum value is not an integer: " + i
            if x in uniqueNames:
                raise EnumException, "enum name is not unique: " + x
            if i in uniqueValues:
                raise EnumException, "enum value is not unique for " + x
            uniqueNames.append(x)
            uniqueValues.append(i)
            v = EnumValue(i, x)
            lookup[x] = v
            reverseLookup[i] = v
            i = i + 1
        self.lookup = lookup
        self.reverseLookup = reverseLookup
       
    
    def add(self, i, x): 
        v = EnumValue(i, x)
        self.lookup[x] = v
        self.reverseLookup[i] = v
        
    def __getattr__(self, attr):
        if not self.lookup.has_key(attr):
            raise AttributeError
        return self.lookup[attr]
       
    def byid(self, value):
        if isinstance(value, (str, unicode)):
            value = int(value)
        if value not in self.reverseLookup:
            self.add(value, 'UNKNOWN_ENUM')
        return self.reverseLookup[value]
        
