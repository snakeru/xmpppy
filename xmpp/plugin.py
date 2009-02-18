##   Copyright (C) 2003-2009 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

__doc__="Provides PlugIn class functionality to develop extentions for xmpppy."

class PlugIn:
    """ Common xmpppy plugins infrastructure: plugging in/out, debugging. """
    def __init__(self):
        self._exported_methods=[]
        self.DBG_LINE=self.__class__.__name__.lower()

    def PlugIn(self,owner):
        """ Attach to main instance and register ourself and all our staff in it. """
        self._owner=owner
        if self.DBG_LINE not in owner.debug_flags:
            owner.debug_flags.append(self.DBG_LINE)
        self.DEBUG('Plugging %s into %s'%(self,self._owner),'start')
        if self.__class__.__name__ in owner.__dict__:
            return self.DEBUG('Plugging ignored: another instance already plugged.','error')
        self._old_owners_methods=[]
        for method in self._exported_methods:
            if method.__name__ in owner.__dict__:
                self._old_owners_methods.append(owner.__dict__[method.__name__])
            owner.__dict__[method.__name__]=method
        owner.__dict__[self.__class__.__name__]=self
        if 'plugin' in self.__class__.__dict__: return self.plugin(owner)

    def PlugOut(self):
        """ Unregister all our staff from main instance and detach from it. """
        self.DEBUG('Plugging %s out of %s.'%(self,self._owner),'stop')
        self._owner.debug_flags.remove(self.DBG_LINE)
        for method in self._exported_methods: del self._owner.__dict__[method.__name__]
        for method in self._old_owners_methods: self._owner.__dict__[method.__name__]=method
        del self._owner.__dict__[self.__class__.__name__]
        if 'plugout' in self.__class__.__dict__: return self.plugout()

    def DEBUG(self,text,severity='info'):
        """ Feed a provided debug line to main instance's debug facility along with our ID string. """
        self._owner.DEBUG(self.DBG_LINE,text,severity)
