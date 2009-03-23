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

def read_jad(file):
    """ Read a Java .jad file. Ignores any errors.
    
    Returns a dictionary containing the data.
    """
    result = {}
    for line in file:
       i = line.find(':') 
       if i >= 0:
           key = line[:i]
           value = line[i+1:].strip()
           result[key] = value
    return result

def parse_url(url):
    a = url.find('://')
    b = a + 3
    c = url.find(':', b)
    d = c + 1
    e = url.find('/', d)
    
    protocol = url[:a]
    host = url[b:c]
    
    if e >= d:
        path = url[e:]
        port = int(url[d:e])
    else:
        path = None
        port = int(url[d:])
    return (protocol, host, port, path)