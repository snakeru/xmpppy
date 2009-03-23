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

from datetime import datetime
from copy import copy
import logging
import exceptions

from mxit.enum import Enumeration
from mxit.util import update

logger = logging.getLogger("libmxit.handles")

BuddyType = Enumeration('BuddyType', [
    ('MXIT', 0),
    ('JABBER', 1),
    ('SERVICE', 8),
    ('SERVICE2', 9),
    ('GALLERY', 12),
    ('INFO', 13),
    ('ROOM', 14),
])

Presence = Enumeration('Presence', [
    ('OFFLINE', 0),
    ('AVAILABLE', 1),
    ('AWAY', 2),
    ('CHAT', 3),
    ('BUSY', 4),
    ('XA', 5),
    ('PENDING', 98),    # Buddy invited us
    #('NONE', 99),       # Not in buddy list 
    
])

Mood = Enumeration('Mood', [
    ('NONE', 0),
    ('ANGRY', 1),
    ('EXCITED', 2),
    ('GRUMPY', 3),
    ('HAPPY', 4),
    ('INLOVE', 5),
    ('INVINCIBLE', 6),
    ('SAD', 7),
    ('HOT', 8),
    ('SICK', 9),
    ('SLEEPY', 10),
])

Gender = Enumeration('Gender', [
    ('FEMALE', 0),
    ('MALE', 1),
])

PrivateNumber = Enumeration('PrivateNumber', [
    ('NO', 0),
    ('YES', 1),
])

Mood.NONE.text = ''
Mood.ANGRY.text = 'Angry'
Mood.EXCITED.text = 'Excited'
Mood.GRUMPY.text = 'Grumpy'
Mood.HAPPY.text = 'Happy'
Mood.INLOVE.text = 'In love'
Mood.INVINCIBLE.text = 'Invicible'
Mood.SAD.text = 'Sad'
Mood.HOT.text = 'Hot'
Mood.SICK.text = 'Sick'
Mood.SLEEPY.text = 'Sleepy'


MessageType = Enumeration('MessageType', [
    ('TEXT', 1),
    ('NOTICE', 2),     #eg. "xxx has left the room"
    ('COMMAND', 7),    # May contain menu's
])
              

StatusChangeReason = Enumeration('StatusChange', [
    'UNKNOWN',
    'REQUESTED',
    'NETWORK_ERROR',
    'TIMEOUT',
    'AUTH_FAILED',
    'ERROR',
])

Status = Enumeration('Status', [
    'DISCONNECTED',
    'CONNECTING',
    'AUTHENTICATING',
    'ACTIVE',
    'DISCONNECTING',
])

Subscription = Enumeration('Subscription', [
    'NONE',
    'INVITED',
    'SUBSCRIBED',
])
  
class Group:
    def __init__(self, name):
        self.name = name
        self._buddies = []
        
    def is_root(self):
        return len(self.name) == 0
    
    def __str__(self):
        return self.name
        
    def __repr__(self):
        return str(self)
    
    
class Room(object):
    def __init__(self, jid, name, group, type=BuddyType.ROOM, presence=Presence.AVAILABLE, mood=Mood.NONE):
        self.jid = jid
        self.name = name
        self.group = group            
        self.type = type
        self.presence = presence
        self.mood = mood
        self._buddies = set()
    
    @property    
    def buddies(self):
        return self._buddies
    
    def joined_buddies(self, buddies):
        """ Indicate that the specified buddies joined the room.
        
        A set of the new buddies is returned.
        """
        joinedbuddies = set(buddies)
        newbuddies = joinedbuddies.difference(self._buddies)
        self._buddies.update(newbuddies)
        return newbuddies
    
    
    def left_buddies(self, buddies):
        """ Indicate that the specified buddies left the room.
        
        A set of the buddies that were in the room is returned.
        """
        leftbuddies = set(buddies)
        actualbuddies = leftbuddies.union(self._buddies)
        self._buddies.difference_update(actualbuddies)
        return actualbuddies
        
    def contains_buddies(self, buddies):
        """ Indicate that the specified buddies are in the room.
        
        A set of buddies that left, and a set of buddies that joined is returned.
        """
        cbuddies = set(buddies)
        left = self._buddies.difference(cbuddies)
        joined = cbuddies.difference(self._buddies)
        self._buddies = cbuddies
        return (left, joined)
        
    def is_room(self):
        return True
    
    def is_subscribed(self):
        return self.presence != Presence.PENDING
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return "<Room %s>" % str(self)
    
    def __eq__(self, buddy):
        return self.jid == buddy.jid
    
class Buddy(object):
#    def __new__(self, jid, name, group, type=BuddyType.MXIT, presence=Presence.NONE, mood=Mood.NONE):
#        if type == BuddyType.ROOM:
#            logger.info("New room: %s" % jid)
#            return object.__new__(Room, jid, name, group, presence=presence, mood=mood)
#        else:
#            logger.info("New buddy: %s" % jid)
#            return object.__new__(Buddy, jid, name, group, presence=presence, mood=mood, type=type)
        
    def __init__(self, jid, name, group, type=BuddyType.MXIT, presence=Presence.OFFLINE, mood=Mood.NONE, is_self=False):
        if type == BuddyType.ROOM:
            raise exceptions.Exception("ROOM buddy must be a Room")
        self.jid = jid
        self.name = name
        self.group = group            
        self.type = type
        self.presence = presence
        self.mood = mood
        self.is_self = is_self
        
        self._buddies = set()
        
    def is_room(self):
        return False
    
    def is_subscribed(self):
        return self.presence != Presence.PENDING
        
    
    def __eq__(self, buddy):
        return self.jid == buddy.jid
        
    def __str__(self):
        return "%s <%s>" % (self.name, self.jid)
    
    def __repr__(self):
        return "<Buddy %s>" % str(self)

class ChatBuddy(object):
    def __init__(self, name):
        self.name = name
        
    
    
class Roster:
    def __init__(self, con):
        self._buddies = {}
        self._chat_buddies = {}
        self._rooms = {}
        self._groups = {}
        self._files = {}
        self.con = con
        self.self_buddy = Buddy(jid=u'', name=None, group=self.root_group, presence=Presence.AVAILABLE, is_self=True)
        
        
        
    def get_group(self, name):
        name = self.con.ee(name)
        if name in self._groups:
            return self._groups[name]
        else:
            self._groups[name] = Group(name)
            return self._groups[name]
        
    @property
    def root_group(self):
        return self.get_group(u'')
        
    @property
    def info_buddy(self):
        for jid, buddy in self._buddies.items():
            if buddy.type == BuddyType.INFO:
                return buddy
        return None
    
    def update_buddy(self, jid, **attrs):
        """ Should only be called from the connection. """
        if jid in self._buddies:
            buddy = self._buddies[jid]
            updated = update(buddy, **attrs)
            return (buddy, False, updated)
        else:
            buddy = Buddy(jid=jid, **attrs)
            self._buddies[jid] = buddy
            return (buddy, True, {})
        
    def update_room(self, jid, **attrs):
        """ Should only be called from the connection. """
        if jid in self._rooms:
            room = self._rooms[jid]
            updated = update(room, **attrs)
            return (room, False, updated)
        else:
            room = Room(jid=jid, **attrs)
            self._rooms[jid] = room
            return (room, True, {})
    
    def create_buddy(self, buddy):
        """ Should only be called from the connection. """
        if buddy.jid in self._buddies:
            raise exceptions.Exception("Buddy already exists")
        self._buddies[buddy.jid] = buddy
        
    
    def create_room(self, room):
        """ Should only be called from the connection. """
        if room.jid in self._rooms:
            raise exceptions.Exception("Room already exists")
        self._rooms[room.jid] = room
         
    def get_buddy(self, jid):
        jid = self.con.ee(jid)
        if jid in self._buddies:
            return self._buddies[jid]
        elif jid == self.self_buddy.jid:
            return self.self_buddy
        else:
            return None
    
    def get_room(self, jid):
        jid = self.con.ee(jid)
        
        if jid in self._rooms:
            return self._rooms[jid]
        else:
            return None
    
        
    def all_buddies(self):
        return self._buddies.values()
    
    def all_rooms(self):
        return self._rooms.values()
    
    def buddy_or_room(self, jid):
        return self.get_buddy(jid) or self.get_room(jid)
    
    def find_buddy(self, name):
        if name:
            for jid, buddy in self._buddies.items():
                if buddy.name == name:
                    return buddy
        return None
    
    def find_room(self, name):
        if name:
            for jid, room in self._rooms.items():
                if room.name == name:
                    return room
        return None
    
    def remove_buddy(self, buddy):
        del self._buddies[buddy.jid]

    def remove_room(self, room):
        del self._rooms[room.jid]
        
    def has_buddy(self, jid):
        return jid in self._buddies
    
    def has_room(self, jid):
        return jid in self._rooms
    
    def chat_buddy(self, name):
        name = self.con.ee(name)
        if name in self._chat_buddies:
            return self._chat_buddies[name]
        else:
            b = ChatBuddy(name)
            self._chat_buddies[name] = b
            return b
        
    def add_file(self, file):
        self._files[file.id] = file
    
def mtd(s):
    result = {}
    for a in s.split('|'):
        key, value = a.split('=')
        result[key] = value
    return result

class Message:
    def __init__(self, buddy, message, time=None, type=MessageType.TEXT):
        if time == None:
            time = datetime.now()
        self.buddy = buddy
        self._message = message
        self._parsed = None
        self.type = type
        self.id = id
        self.time = time
        
        self._parse_message()
        
    def _parse_message(self):
        if self.type == MessageType.COMMAND:
            try:
                msg = self._message
                newmsg = ""
                end = 0
                while True:
                    i = msg.find('::', end)
                    if i < 0:
                        newmsg += msg[end:]
                        break
                    newmsg += msg[end:i]
                    i += 2
                    end = msg.find(':', i)
                    if end >= i:
                        d = mtd(msg[i:end])
                        if 'replymsg' in d:
                            if d['replymsg'] in d['selmsg']:
                                newmsg += d['selmsg']
                            else:
                                newmsg += d['replymsg'] + ')'
                        else:
                            newmsg += d['selmsg']
                    end += 1
                self._parsed = newmsg
            except exceptions.Exception, e:
                logger.exception(e)
                self._parsed = self._message
        else:
            self._parsed = self._message
            
    @property
    def message(self):
        return self._parsed
    
    @property
    def raw_message(self):
        return self._message
    
    def __str__(self):
        return "%s: %s" % (self.buddy.name, self.message)
    
    def __repr__(self):
        return "<Message %s>" % str(self)
    
class RoomMessage(Message):
    def __init__(self, roster, room, message, time=None, type=MessageType.TEXT):
        Message.__init__(self, room, message, time=time, type=type)
        self.sender = sender
        
        
    
    def __str__(self):
        return "%s - %s: %s" % (self.buddy.name, self.sender and self.sender.name or '', self.room_message)
    
    def __repr__(self):
        return "<RoomMessage %s>" % str(self)
    
class FileDescriptor:
    def __init__(self, id, size=None, name=None, mimetype=None, description=None):
        self.id = id
        self.size = size
        self.name = name
        self.mimetype = mimetype
        self.description = description
        
