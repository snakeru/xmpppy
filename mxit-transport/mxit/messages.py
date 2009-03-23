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

from mxit.handles import *
from mxit.commands import *
from mxit.encryption import client_id, encode_password
from mxit.util import update, find_attrs
from mxit.binary import BinaryStream

import logging

logger = logging.getLogger("libmxit.messages")

def build_cmd(con, data):
    """ Build a command for sending. """
    
    bits = []
    for a in data:
        if isinstance(a, (tuple, list)):
            bits.append('\1'.join(map(con.to_mxit, a)))
        else:
            bits.append(con.to_mxit(a))
    return '\0'.join(bits)


    
class ServerMessage:
    def __init__(self, command, response, data):
        self.command = command
        self.response = response
        self.data = data

        
class ClientMessage:
    def __init__(self, command):
        self.command = command
        
    def send(self, socket):
        """ Write the message to the specified socket. """
        pass
    
    def should_wait(self):
        """ Whether or not the connection should wait to receive a response for this message.
        
        No other commands will be sent while waiting.
        """
        return False
    
    def received(self, server_message):
        """ Check a message for the response.
        
        This should return True if it is a valid response, false if it is another command.
        
        If it is a valid response, no further processing will be done on the message.
        If not, the connection will keep waiting for a valid response, or until the timeout expired.
        """
        return True
    
    def timeout(self):
        """ Called when no response is received within a reasonable time limit. """
        pass
    
    
    
class StandardMessage(ClientMessage):
    def __init__(self, con, command, data, wait=False, multiple=True):
        ClientMessage.__init__(self, command)
        self.con = con
        self.data = data
        self.wait = wait
        self.multiple = multiple
        
    def should_wait(self):
        return self.wait
    
    def check(self, message):
        return message.command.id == self.command.id
    
    def received(self, server_message):
        return self.check(server_message)
    
    def timeout(self):
        logger.error("No response received for %s" % self.command)
        self.con._set_status(Status.DISCONNECTED, StatusChangeReason.TIMEOUT)
        
    def send(self, socket):
        data = self.data
        command = self.command
        logger.info("~ sending ~ %r ~ %s" % (command, data))
        if isinstance(data, (tuple, list)):
            data = build_cmd(self.con, data)
            
        newstr = "id=" + self.con.to_mxit(self.con.id) + "\0cm=" + self.con.to_mxit(command.id) + "\0ms=" + data
        newstr = "ln=" + self.con.to_mxit(len(newstr)) + "\0" + newstr
        
        socket.sendall(newstr)
        
    def __repr__(self):
        return "<StandardMessage %s>" % str(self)
    
    def __str__(self):
        return "%r: %r" % (self.command, self.data)
        
class BlankMessage(StandardMessage):
    def __init__(self, con, command, wait=True, multiple=True):
        StandardMessage.__init__(self, con, command, None, wait, multiple)
        
    def send(self, socket):
        command = self.command
        logger.info("~ sending ~ %s" % (command))
                    
        newstr = "id=" + self.con.to_mxit(self.con.id) + "\0cm=" + self.con.to_mxit(command.id)
        newstr = "ln=" + self.con.to_mxit(len(newstr)) + "\0" + newstr
        
        socket.sendall(newstr)

class BinaryMessage(ClientMessage):
    def __init__(self, con, command, signature, data=[]):
        ClientMessage.__init__(self, Client.BINARY)
        self.con = con
        self.sig = signature
        self.command = command
        self.data = data
        
    def should_wait(self):
        return True
    
    def check(self, message):
        return message.command == self.command
    
    def received(self, message):
        return self.check(message)
    
    def send(self, socket):
        command = Client.BINARY
        logger.info("~ sending ~ %r ~ %s" % (command, self.data))
        
        stream = BinaryStream(self.con)
        data = stream.write(self.sig, *self.data)
        if data:
            for d in data:
                stream.write_bytes(d)
        
        stream2 = BinaryStream(self.con)
        stream2.write('BI', self.command.id, len(stream))
        stream2.write_bytes(stream.data)
        
        data = stream2.data
        newstr = "id=" + self.con.to_mxit(self.con.id) + "\0cm=" + self.con.to_mxit(command.id) + "\0ms=" + data
        newstr = "ln=" + self.con.to_mxit(len(newstr)) + "\0" + newstr
        
        socket.sendall(newstr)
        
    def __repr__(self):
        return "<BinaryMessage %s>" % str(self)
    
    def __str__(self):
        return "%r: %r" % (self.command, self.data)
    
class FileRequestMessage(BinaryMessage):
    def __init__(self, con, f):
        BinaryMessage.__init__(self, con, Binary.REQUEST_FILE, 'QII')
        self.data = [f.id, 0, f.size]
        self.f = f
        
    def received(self, message):
        if not self.check(message):
            return False
        
        data = message.data
        id, mid, filelen, end = data.read('QIII')
        filedata = data.read_bytes(filelen)
        logger.info("%s, %s, %s" % (id, mid, end))
        logger.info("file data: %s" % repr(filedata))
        self.con.s(FileAckMessage, self.f)
        self.con.listeners.file_received(self.f, filedata)
        return True
        
class FileAckMessage(BinaryMessage):
    def __init__(self, con, f):
        BinaryMessage.__init__(self, con, Binary.ACK_FILE, 'QB')
        self.data = [f.id, 1]

class FileForwardMessage(BinaryMessage):
    def __init__(self, con, f, recipient):
        BinaryMessage.__init__(self, con, Binary.FORWARD_FILE, 'QHS')
        self.data = [f.id, 1, recipient.jid]
       
class FileSendMessage(BinaryMessage):
    def __init__(self, con, f, recipient, filedata):
        BinaryMessage.__init__(self, con, Binary.SEND_FILE, 'IHSSSSI')
        self.data = [len(filedata), 1, recipient.jid, f.name, f.mimetype, f.description, 0, filedata] 
        self.filedata = filedata
        
    def send(self, socket):
        BinaryMessage.send(self, socket)
        logger.info("file data: %s" % self.filedata)
        #socket.sendall(self.filedata)
                
class EditMessage(StandardMessage):
    def __init__(self, con, buddy, **attrs):
        if 'name' in attrs:
            name = attrs['name']
        else:
            name = buddy.name
        if 'group' in attrs:
            group = attrs['group']
        else:
            group = buddy.group
        StandardMessage.__init__(self, con, Client.EDIT_BUDDY, [[group.name, buddy.jid, name]], wait=True)
        self.con = con
        self.buddy = buddy
        self.attrs = attrs
        
        
    def received(self, message):
        if not self.check(message):
            return False
        if message.response.code == 0:
            updated = update(self.buddy, **self.attrs)
            if self.buddy.is_room():
                self.con.listeners.room_updated(self.buddy, **updated)
            else:
                self.con.listeners.buddy_updated(self.buddy, **updated)
        else:
            logger.error("Error received in response to buddy edit: %s" % message.response)
        return True
    
class LoginMessage(StandardMessage):
    def __init__(self, con):
        StandardMessage.__init__(self, con, Client.LOGIN, [[encode_password(con.client_id, con.password), con.java_env, 1, con.features, client_id(con.client_id), 255, con.country_code, con.language], ["cr=%s" % con.splash]], wait=True)
        
    def received(self, message):
        if not self.check(message):
            return False
        logger.info("Login response received")
        if message.response.code == 0:
            self.con._set_status(Status.ACTIVE)
        elif message.response.code == 16:
            r = message.response.message.split(';')[0]
            
            if r.startswith('socket://'):
                r = r[len('socket://'):]
                
            server, port = r.split(':')
            
            self.con._close()
            self.con._set_status(Status.DISCONNECTED, StatusChangeReason.NETWORK_ERROR)
            
            self.con.listeners.redirected(server, int(port))
            #self.con._redirect(server, int(port))
            
        else:
            logger.error("Error logging in: %s" % message.response)
            self.con._close()
            self.con._set_status(Status.DISCONNECTED, StatusChangeReason.AUTH_FAILED)
        return True
    
class TextMessage(StandardMessage):
    def __init__(self, con, message):
        StandardMessage.__init__(self, con, Client.MESSAGE, [[message.buddy.jid, message.message, message.type.id, 0]], wait=True)
        self.message = message
        
    def received(self, message):
        if not self.check(message):
            return False
        if message.response.code == 0:
            logger.info("Message delivered: %s" % self.message.message)
            self.con.listeners.message_delivered(self.message)
        else:
            logger.info("Error delivering message: %s" % message.response)
            self.con.listeners.message_error(self.message, message.response.message)
        return True
    
    def send(self, socket):
        StandardMessage.send(self, socket)
        self.con.listeners.message_sent(self.message)
    
class RemoveBuddyMessage(StandardMessage):
    def __init__(self, con, buddy):
        StandardMessage.__init__(self, con, Client.REMOVE_BUDDY, [[buddy.jid]], wait=True)
        self.buddy = buddy
        
    def received(self, message):
        if not self.check(message):
            return False
        if message.response.code == 0:
            logger.info("buddy removed: %s" % self.buddy.name)
            if self.buddy.is_room():
                self.con.roster.remove_room(self.buddy)
                self.con.listeners.room_removed(self.buddy)
            else:
                self.con.roster.remove_buddy(self.buddy)
                self.con.listeners.buddy_removed(self.buddy)
        else:
            logger.info("Error removing buddy: %s" % message.response)
        return True
    
class MoodMessage(StandardMessage):
    def __init__(self, con, mood):
        StandardMessage.__init__(self, con, Client.MOOD, [[mood.id]], wait=True, multiple=False)    #TODO: test
        self.con = con
        self.mood = mood
        
    def timeout(self):
        pass
    
    def received(self, message):
        if not self.check(message):
            return False
        
        self.con.listeners.mood_changed(self.mood)
        return True
    
class PresenceMessage(StandardMessage):
    def __init__(self, con, presence):
        StandardMessage.__init__(self, con, Client.PRESENCE, [[presence.id, '']], wait=True, multiple=False)
        self.con = con
        self.presence = presence
        
    def received(self, message):
        if not self.check(message):
            return False
        
        self.con.listeners.presence_changed(self.presence)
        return True
        

    
class LogoutMessage(StandardMessage):
    def __init__(self, con):
        StandardMessage.__init__(self, con, Client.LOGOUT, [0], wait=True, multiple=False)
        self.con = con
        
    def received(self, message):
        if not self.check(message):
            return False
        
        logger.info("logout response")
        self.con._close()
        self.con._set_status(Status.DISCONNECTED, StatusChangeReason.REQUESTED)
        return True
        
class PingMessage(BlankMessage):
    def __init__(self, con):
        BlankMessage.__init__(self, con, Client.PING, wait=True, multiple=False)
        
    def received(self, message):
        if not self.check(message):
            return False
        
        if message.data:
            return False
        
        return True
        
        
    def timeout(self):
        logger.error("No ping response received")
        self.con._set_status(Status.DISCONNECTED, StatusChangeReason.TIMEOUT)
                
        
class CreateRoomMessage(StandardMessage):
    def __init__(self, con, name, buddies):
        StandardMessage.__init__(self, con, Client.CREATE_ROOM, [[name, len(buddies)] + [buddy.jid for buddy in buddies]], wait=True)
        self.con = con
        self.name = name
        self.buddies = buddies
        
    def received(self, message):
        if not self.check(message):
            return False
        
        if message.response.code == 0:
            room_id = message.data[0][0]
            logger.info("Room created: %s" % room_id)
        else:
            self.con.listeners.room_create_error(self.name, message.response)
            logger.error("Cannot create room: %s" % message.response.message)
        
        return True
    
class RoomInviteMessage(StandardMessage):
    def __init__(self, con, room, buddies):
        StandardMessage.__init__(self, con, Client.ROOM_INVITE, [[room.jid, len(buddies)] + [buddy.jid for buddy in buddies]], wait=True)
        self.con = con
        self.room = room
        self.buddies = buddies
        
    def received(self, message):
        if not self.check(message):
            return False
        
        if message.response.code == 0:
            room_id = message.data[0][0]
            logger.info("Room invited: %s" % room_id)
            
        else:
            logger.error("Cannot invite %s to room: %s" % ([buddy.name for buddy in self.buddies], message.response.message))
        
        return True
    
class BuddyInviteMessage(StandardMessage):
    def __init__(self, con, jid, name, group):
        StandardMessage.__init__(self, con, Client.INVITE, [[group.name, jid, name, '']], wait=True)
        self.con = con
        self.id = id
        self.jid = jid
        self.group = group
        self.name = name
        
    def received(self, message):
        if not self.check(message):
            return False
        
        if message.response.code == 0:
            pass
        else:
            logger.error("Cannot invite %s: %s" % (self.jid, message.response))
        
        return True
    
class AcceptInviteMessage(StandardMessage):
    def __init__(self, con, buddy):
        StandardMessage.__init__(self, con, Client.ACCEPT_INVITE, [[buddy.jid, buddy.group.name, buddy.name]], wait=True)
        self.con = con
        self.buddy = buddy
        
    def received(self, message):
        if not self.check(message):
            return False
        
        if message.response.code == 0:
            pass
        else:
            logger.error("Cannot accept invite of %s: %s" % (self.buddy.jid, message.response))
        
        return True

class ProfileRequestMessage(BlankMessage):
    def __init__(self, con):
        BlankMessage.__init__(self, con, Client.PROFILE_REQUEST, wait=True, multiple=False)
        
    def received(self, message):
        if not self.check(message):
            return False
        
        if message.response.code == 0:
            logger.info("Profile response: %s" % (message.data))
            name, private_id, birthdate, gender_id, q = message.data[0]
            private = PrivateNumber.byid(private_id)
            gender = Gender.byid(gender_id)
            
            
            profile = self.con.roster.self_buddy
            
            updated = update(profile, name=name, birthdate=birthdate, private=private, gender=gender)
            
            if updated:
                self.con.listeners.profile_updated(profile, **updated)
        else:
            logger.error("Error requesting profile: %s" % (message.response))
        
        return True
        
class ProfileUpdateMessage(StandardMessage):
    def __init__(self, con, password=None, **attrs):
        profile = con.roster.self_buddy
        values = find_attrs(profile, dict(name='You', private=PrivateNumber.YES, birthdate='1990-01-01', gender=Gender.MALE), **attrs)
        self.values = values        
        if not password:
            password = con.password
            
        pin = encode_password(con.client_id, password)
        
        StandardMessage.__init__(self, con, Client.PROFILE, [[pin, str(values['name']), values['private'].id, str(values['birthdate']), values['gender'].id, '']], wait=True, multiple=False)
    
    def received(self, message):
        if not self.check(message):
            return False
        
        if message.response.code == 0:
            profile = self.con.roster.self_buddy
            updated = update(profile, **self.values)
            if updated:
                self.con.listeners.profile_updated(profile, **updated)
        else:
            logger.error("Cannot update profile: %s" % (message.response))
        
        return True
