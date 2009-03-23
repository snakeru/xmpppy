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
import gobject
import sys
import exceptions
import traceback

from mxit.connection import MxitConnection


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("libmxit.main")


file = open("account", "r")
username = file.readline().strip()
password = file.readline().strip()
jid = file.readline().strip()
file.close()

con = MxitConnection(id=username, password=password, client_id=jid)
con.java_env = 'E-5.2.1-1.1'

class Listener:
    def message_received(self, message):
        print message
        
    def buddy_added(self, buddy):
        print buddy
        
    def presence_changed(self, buddy):
        print buddy
        
        
def read_input(*vargs):
    try:
        line = raw_input()
        exec(line)
    except exceptions.Exception, e:
        import traceback
        traceback.print_exc()
    
    #gobject.idle_add(read_input)
    return True
    
    
con.listeners.add(Listener())
logger.info("connecting...")
con.connect()
gobject.io_add_watch(sys.stdin, gobject.IO_IN, read_input)
gobject.MainLoop().run()
#
#print "done"
#buddy = None
#while True:
#    line = raw_input().strip()
#    if line == 'q':
#        break
#    if con.roster.has_buddy(line):
#        buddy = con.roster.get_buddy(line)
#        print "Sending to: %s" % buddy.name
#    elif buddy:
#        con.message(buddy, line)
#        
#print "Closing connection...",
con.close()
con.join()
print "done"
