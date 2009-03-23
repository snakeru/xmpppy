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

import logging

logger = logging.getLogger("libmxit.events")

class EventManager:
    """
    EventManager is a proxy for event method calls.
    
    Whenever any method is called on an EventManager, that method is called 
    on each listener that defines it. Nothing is returned.
    """
    
    def __init__(self, listeners=[]):
        """
        Create a new EventManager with the specified listeners.
        """
                
        self._listeners = set()
        self._listeners.update(listeners)
        
    def add(self, listener):
        """
        Add the listener to the EventManager.
        """
        
        self._listeners.add(listener)
        
    def remove(self, listener):
        """
        Remove the listener from the EventManager
        """
        
        self._listeners.remove(listener)
        
    def __getattr__(self, attr):
        #TODO: exceptions
        def call(*vargs, **kwargs):
            #logger.debug("event %s with %r" % (attr, vargs))
            for listener in self._listeners:
                if hasattr(listener, attr):
                    f = getattr(listener, attr)
                    f(*vargs, **kwargs)
                            
        return call