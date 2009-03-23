# This file is part of PyMXit, a Python library implementing the basic
# functionality of the MXit protocol.
#
# Copyright (C) 2008 Ralf Kistner <ralf.kistner@gmail.com>
# 
# PyMXit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# PyMXit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with PyMXit.  If not, see <http://www.gnu.org/licenses/>.

def update(object, **attrs):
    """ Update an object, and return the changed attributes. """
    updated = {}
    for key, value in attrs.items():
        if not hasattr(object, key) or getattr(object, key) != attrs[key]:
            updated[key] = value
            setattr(object, key, value)
    return updated

def set_attrs(object, defaults, **attrs):
    check_attrs(defaults, attrs)
    for key in defaults:
        if key in attrs:
            setattr(object, key, attrs[key])
        else:
            setattr(object, key, defaults[key])
            
def find_attrs(object, defaults, **prefered):
    result = {}
    for key in defaults:
        if key in prefered:
            result[key] = prefered[key]
        elif hasattr(object, key):
            result[key] = getattr(object, key)
        else:
            result[key] = defaults[key]
    return result


def difference(object, **attrs):
    updated = {}
    for key, value in attrs.items():
        if not hasattr(object, key) or getattr(object, key) != attrs[key]:
            updated[key] = value
    return updated

def check_attrs(keys, attrs):
    for key in attrs:
        if key not in keys:
            raise AttributeError("'%s' not allowed" % key)
        
