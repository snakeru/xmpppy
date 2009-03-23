# telepathy-mixer - an MXit connection manager for Telepathy
#
# Copyright (C) 2008 Ralf Kistner <ralf.kistner@gmail.com>
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


import socket
import datetime
import logging
import time
import gobject
import struct
from exceptions import Exception
from Queue import Queue, Empty


from mxit.enum import Enumeration
from mxit.handles import *
from mxit.encryption import client_id, encode_password
from mxit.events import EventManager
from mxit.errors import MxitException
from mxit.commands import Client, Server, Binary
from mxit.messages import *
from mxit.util import difference, check_attrs, set_attrs
from mxit.binary import BinaryStream

logger = logging.getLogger("libmxit.connection")


class MxitConnection:
    
    def __init__(self, **params):
        """
        Create a new connection.
        
        Parameters and defaults:
            host -> 'stream.mxit.co.za'
            port -> 9119
            id -> ''
            password -> ''
            client_id -> '' (from the jad file)
            features -> ''
            java_env -> 'E-5.3.0'
            revision -> 'v5_6'
        """
        
        defaults = {
            'host': 'stream.mxit.co.za',
            'port': 9119,
            'id': None,
            'password': None,
            'client_id': None,
            'features': 'dist=E;ver=5.3.0;cat=J;platform=j2me;width=180;height=196;cols=4096;maxmsg=150000;features=255;ctypes=3;dmem=215000;fmem=986000',
            'splash': '',
            'java_env': 'E-5.3.0',
            'language': 'en',
            'country_code': 27,
            
            'encoding': 'ISO-8859-1',
            'response_timeout': 20.0,        # s
            'ping_interval': 10*60*1000,    # ms
        }
        
        set_attrs(self, defaults, **params)
        
        self.roster = Roster(self)
        self.queue = Queue()
        self.waiting_for = None
        self.listeners = EventManager()
        self.status = Status.DISCONNECTED
        self.sock = None
        self.destroyed = False
        
        
    
    # ----------------
    # PUBLIC FUNCTIONS
    # ----------------
    
    def connect(self):
        """ Connect, login, and listen. """
        
        if self.destroyed:
            raise Exception("Cannot connect again")
        if self.status != Status.DISCONNECTED:
            raise MxitException('Already connected')
        self._set_status(Status.CONNECTING, reason=StatusChangeReason.REQUESTED)
        
        self.buffer = ""
        try:
            self._connect()
        except Exception, e:
            logger.exception(e)
            self._set_status(Status.DISCONNECTED, reason=StatusChangeReason.NETWORK_ERROR)
            
            return
        
        self._set_status(Status.AUTHENTICATING, reason=StatusChangeReason.REQUESTED)
        
        try:
            self._do_login()
        except Exception, e:
            logger.exception(e)
            self._set_status(Status.DISCONNECTED, reason=StatusChangeReason.ERROR)
            return
        
        
        gobject.io_add_watch(self.sock, gobject.IO_IN, self.listen_once)
        gobject.timeout_add(self.ping_interval, self._ping)
        
        self.s(ProfileRequestMessage)
        #self.send_file(FileDescriptor(0, name='test.txt', mimetype='text/plain', description='A test'), Buddy('gallery@services.mxit.co.za', 'Gallery', ''), open('/home/nagapie/test', 'r'))
        
    def close(self):
        """ Logout and close the connection. """
        self.destroyed = True
        
        self.s(LogoutMessage)
        self._set_status(Status.DISCONNECTING, StatusChangeReason.REQUESTED)
        
        #TODO: this can be implemented in the message timeout
        def timeout_cb():
            if self.status != Status.DISCONNECTED:
                logger.error("Logout timed out")
                self._close()
                self._set_status(Status.DISCONNECTED, StatusChangeReason.REQUESTED)
        gobject.timeout_add(5000, timeout_cb)
        
        
    def message(self, buddy, message, type=MessageType.TEXT):
        """ Send a message to the specified buddy. """
        message = self.ee(message)
        self.s(TextMessage, Message(buddy, message, type=type))
        
    
    def set_presence(self, presence):
        """ Set the user's presence.
        
        If the client is not connected yet, the presence is sent after login.
        """
        self.roster.self_buddy.presence = presence
        
        if self.status == Status.ACTIVE:
            self.s(PresenceMessage, presence)
        # If not running, the presence will be set when connected
                
    
    def invite(self, jid, name=None, group=None):
        """ Invite a buddy.
        
        The buddy is only added to the roster when we received a response from the server.
        
        The jid that the server sends back might be different from the one we invited.
        """
        jid = self.ee(jid)
        name = self.ee(name)
        if not name:
            name = jid
        if not group:
            group = self.roster.root_group()

        logger.info("Inviting: %s" % jid)
        self.s(BuddyInviteMessage, jid, name, group)
    
    def accept_invite(self, buddy):
        """ Accept an invitation from a buddy. """
        if buddy.presence != Presence.PENDING:
            logger.error("Attempting to accept invitation from %s, but no invitation was received" % buddy.jid)
        else:
            logger.info("Accepting invitation for %s" % buddy.jid)
            
            self.s(AcceptInviteMessage, buddy)
        
    def reject_buddy(self, buddy):
        """ Reject an invitation from a buddy.
        
        Not implemented yet.
        """
        if buddy.presence == Presence.PENDING:
            logger.error("Rejection not implemented yet")
        else:
            logger.error("Cannot reject %s - not pending" % buddy.jid)
    
    def remove_buddy(self, buddy):
        """ Remove a buddy. """
        if buddy.presence == Presence.PENDING:
            pass    # Reject buddy instead?
        
        if self.roster.has_buddy(buddy.jid) or self.roster.has_room(buddy.jid):
            self.s(RemoveBuddyMessage, buddy)
    
        
    def update_buddy(self, buddy, name=None, group=None):
        """ Update a buddy or room on the server.
        
        The update is only sent to the server if the buddy's details changed.
        """
        
        attrs = {}
        if name is not None:
            name = self.ee(name)
            if name != buddy.name:
                attrs['name'] = name
                
        if group is not None and buddy.group != group:
            attrs['group'] = group
        if attrs:
            if buddy.is_room() and self.roster.has_room(buddy.jid): 
                self.s(EditMessage, buddy, **attrs)
            elif not buddy.is_room() and self.roster.has_buddy(buddy.jid):
                self.s(EditMessage, buddy, **attrs)
            else:
                raise MxitException('Buddy not in roster')
        
    
    def set_mood(self, mood):
        """ Set the user's mood. """
        self.roster.self_buddy.mood = mood
        self.s(MoodMessage, mood)
        
    def create_room(self, name, buddies=[]):
        """ Create a room and invite the specified buddies. """
        name = self.ee(name)
        self.s(CreateRoomMessage, name, buddies)
        
    def leave_room(self, room):
        """ Leave a room. Same as remove_buddy(room). """
        self.s(RemoveBuddyMessage, room)
        
    def invite_buddies_room(self, room, buddies):
        """ Invite buddies to the room. """
        self.s(RoomInviteMessage, room, buddies)
        
    def update_profile(self, **attrs):
        """ Update the user profile.
        
        Valid attributes are: name, birthdate, private, gender.
        """
        if self.roster.self_buddy.name:
            check_attrs(['name', 'birthdate', 'private', 'gender'], attrs)
            if 'name' in attrs:
                attrs['name'] = self.ee(attrs['name'])
            dif = difference(self.roster.self_buddy, **attrs)
            
            if dif:
                self.s(ProfileUpdateMessage, **dif)
        else:
            # Only update profile if we know what it was
            pass
            
    def request_file(self, descriptor):
        self.s(FileRequestMessage, descriptor)
        
    def send_file(self, descriptor, buddy, f):
        data = f.read()
        self.s(FileSendMessage, descriptor, buddy, data)
        
    # -----------------
    # UTILITY FUNCTIONS
    # -----------------
    def allowed(self, c):
        return ord(c) >= 32 or c in '\n\r\t'
    
    def ee(self, s):
        a = filter(self.allowed, unicode(s))
        # Recode: what it would look like when it went through the server
        b = self.to_mxit(a)
        c = self.from_mxit(b)
        return c
    
    def from_mxit(self, s):
        # Encoding errors should never happen here, but we don't want to crash if they do
        return unicode(s, self.encoding, 'replace')
    
    def to_mxit(self, s):
        if isinstance(s, int):
            return str(s)
        else:
            # Replaces invalid characters with '?'
            return s.encode(self.encoding, 'replace')

    def _enqueue(self, msg):
        self.queue.put(msg)
        gobject.idle_add(self.write_once)
        
    def _basic_command(self, command, data):
        self._enqueue(StandardMessage(self, command, data))
        
    def s(self, msgclass, *vargs, **kwargs):
        self._enqueue(msgclass(self, *vargs, **kwargs))
        
                      
    def _set_status(self, status, reason=StatusChangeReason.UNKNOWN):
        self.status = status
        logger.info("Status changed to %s for reason %s" % (status, reason))
        self.listeners.status_changed(status, reason)   
        
    def _do_login(self):
        """ Log in. """
        self.s(LoginMessage)
        presence = self.roster.self_buddy.presence
        if presence != Presence.AVAILABLE:
            logger.info("Initial presence: %s" % self.roster.self_buddy.presence)
            self._presence(presence.id)
           
        
    
    def _ping(self):
        self.s(PingMessage)
        gobject.timeout_add(self.ping_interval, self._ping)
        
    
        
    # -------------------
    # PROCESSING COMMANDS
    # -------------------
    
    def _r_invite(self, message):
        tree = message.data
        jid = tree[0][0]
        name = tree[0][1]
        
        type_id = tree[0][2]
        presence_id = tree[0][3]
        message = tree[0][4]
        random_name = tree[0][5]
        
        type = BuddyType.byid(type_id)
        
        if type == BuddyType.ROOM:
            room = self.roster.get_room(jid)
            if room:
                # We invited him?
                if room.is_subscribed():
                    logger.info("We invited room or know room, auto accepting")
                    self.s(AcceptInviteMessage, room)
                else:
                    logger.info("Room we know of or invited, auto accepting")
                    updated = update(room, name=name, type=type, presence=Presence.PENDING)
                    if updated:
                        self.listeners.room_updated(room, **updated)
                    self.s(AcceptInviteMessage, room)
                    #room.presence = Presence.PENDING
                    #room.name = name
                    
                    #
                    #self.listeners.buddy_updated(buddy, presence=buddy.presence, name=name)
            else:
                logger.info("Room invited us, auto accepting")
                # Buddy invited us
                room = Room(jid, name, self.roster.root_group, presence=Presence.PENDING)
                self.roster.create_room(room)
                self.listeners.room_added(room, message)
                self.s(AcceptInviteMessage, room)
                #self.listeners.buddy_added(buddy)
                
            if message:
                pass
            
            self.message(room, '.list', MessageType.NOTICE)
            
            if random_name:
                buddy = self.roster.find_buddy(random_name)
                if buddy:
                    joined_set = room.joined_buddies([buddy])
                    if joined_set:
                        self.listeners.room_buddies_joined(room, joined_set)
                        
                #msg = Message(room, message, datetime.now(), MessageType.TEXT)
                #self.listeners.message_received(msg)
        else:
            buddy = self.roster.get_buddy(jid)
            if buddy:
                # We invited him?
                if buddy.is_subscribed():
                    logger.info("We invited buddy or know buddy, auto accepting")
                    self.s(AcceptInviteMessage, buddy)
                    return
                else:
                    logger.info("Buddy we know of invited us, not auto accepting")
                    updated = update(buddy, name=name, type=type, presence=Presence.PENDING)
                    self.listeners.buddy_updated(buddy, **updated)
                    #buddy.presence = Presence.PENDING
                    #buddy.name = name
                    #buddy.type = type
                    #self.listeners.buddy_updated(buddy, presence=buddy.presence, name=name)
            else:
                logger.info("Buddy invited us, not auto accepting")
                # Buddy invited us
                buddy = Buddy(jid, name, self.roster.root_group, type=type, presence=Presence.PENDING)
                self.roster.create_buddy(buddy)
                self.listeners.buddy_added(buddy)
            if message:
                msg = Message(buddy, message, datetime.now(), MessageType.TEXT)
                self.listeners.message_received(msg)
            
    
    def _r_logout(self, message):
        self._close()
        logger.info("Logout received")
        if self.status == Status.DISCONNECTING:
            self._set_status(Status.DISCONNECTED, StatusChangeReason.REQUESTED)
        else:
            self._set_status(Status.DISCONNECTED)
        
    def _r_message(self, message):
        tree = message.data
        from_jid = tree[0][0]
        time = tree[0][1]
        time = datetime.fromtimestamp(int(time))
        type = MessageType.byid(int(tree[0][2]))
        q = tree[0][3]
        r = tree[0][4]
        if r == '16':
            #Encrypted message
            pass
        msg = tree[1][0]
        buddy = self.roster.buddy_or_room(from_jid)
        if buddy.is_room():
            message = Message(buddy, msg, time=time, type=type)
            self._r_room_message(message)
            #self.listeners.message_received(message)
        else:
            message = Message(buddy, msg, time=time, type=type)
            self.listeners.message_received(message)
        
    def _r_room_message(self, message):
        text = message.message
        room = message.buddy
        s = text.find('<')
        e = text.find('>\n')
        if s == 0 and e > 0:
            sender_name = text[s+1:e]
            #sender = self.roster.find_buddy(sender_name)
            sender = self.roster.chat_buddy(sender_name)
            
            joined_set = room.joined_buddies([sender])
            if joined_set:
                self.listeners.room_buddies_joined(room, joined_set)
            room_message = text[e+2:]
            logger.info("room %s|%s:%s" % (room.name, sender_name, room_message))
            msg = Message(sender, room_message, time=message.time, type=message.type)
            self.listeners.room_message_received(room, msg)
            return
        
        if message.type == MessageType.NOTICE:
            i = text.find(' has left.')
            if i > 0:
                left_name = text[:i]
                left = self.roster.chat_buddy(left_name)
                #left = self.roster.find_buddy(left_name)
                logger.info("room %s|%s left" % (room.name, left_name))
                left_set = room.left_buddies([left])
                
                if left_set:
                    self.listeners.room_buddies_left(room, left_set)
                
                return
            
            joiners = []
            i = text.find(' has joined.')
            if i > 0:
                joiner_name = text[:i]
                #joiner = self.roster.find_buddy(joiner_name)
                joiner = self.roster.chat_buddy(joiner_name)
                logger.info("room %s|%s joined" % (room.name, joiner_name))
                joiners = [joiner]
                joined_set = room.joined_buddies(joiners)
                if joined_set:
                    self.listeners.room_buddies_joined(room, joined_set)
                return
                
            
            f = 'The following users are in this MultiMx:\n'
            if text.startswith(f):
                names = text[len(f):].split('\n')
                buddies = []
                for name in names:
                    if name:
                        #buddy = self.roster.find_buddy(name)
                        buddy = self.roster.chat_buddy(name)
                        buddies.append(buddy)
                logger.info("room %s|%s in room" % (room.name, [buddy.name for buddy in joiners]))
                
                left, joined = room.contains_buddies(buddies)
                if left:
                    self.listeners.room_buddies_left(room, left)
                if joined:
                    self.listeners.room_buddies_joined(room, joined)
                return
            
        self.listeners.room_message_received(message)
        
    def _r_presence(self, message):
        tree = message.data
        for child in tree:
            if len(child) != 6:
                if len(child) > 1:
                    raise MxitException("Invalid length for presence command: %s", str(child))
                continue
            group, jid, name, presence, type, mood = child
            presence = Presence.byid(presence)
            group = self.roster.get_group(group)
            mood = Mood.byid(mood)
            type = BuddyType.byid(type)
            
            if type == BuddyType.ROOM:
                if new:
                    self.listeners.room_added(room)
                else:
                    if attrs:
                        self.listeners.room_updated(room, **attrs)
            else:
                buddy, new, attrs = self.roster.update_buddy(jid, name=name, group=group, mood=mood, presence=presence, type=type)
                if new:
                    self.listeners.buddy_added(buddy)
                else:
                    if attrs:
                        self.listeners.buddy_updated(buddy, **attrs)
                
    def _parse_splash(self, message):
        data = message.data
        r = data.read('SSBI')
        screenname, filename, flag, filelen = r
        logger.info("Splash: %s" % (r))
        filedata = data.read_bytes(filelen)
        if filelen > 11:
            random_data = filedata[:11]
            filedata = filedata[11:]
            logger.info("Splash file data: %s" % repr(filedata))
        else:
            logger.info("No splash received")
            
        
    def _parse_filedesc(self, message):
        data = message.data
        r = data.read('QSISSQSSI')
        time1, contact, filelen, filename, mimetype, time2, description, message, end = r
        f = FileDescriptor(time1, name=filename, size=filelen, mimetype=mimetype, description=description)
        buddy = self.roster.get_buddy(contact)
        self.roster.add_file(f)
        logger.info("Filedesc: %s" % (r))
        self.listeners.file_pending(f, buddy)
        
    # ----------------
    # SOCKET HANDLING
    # ----------------
    
    def listen_once(self, *vargs):
        """ Listen for data from the server.
        
        Must be called repetitively.
        """
        try:
            data = self.sock.recv(1024)
            if not data:
                self._close()
                if self.status != Status.DISCONNECTED:
                    self._set_status(Status.DISCONNECTED, StatusChangeReason.NETWORK_ERROR)
                
                return False
        except Exception, e:
            self._close()
            if self.status != Status.DISCONNECTED:
                self._set_status(Status.DISCONNECTED, StatusChangeReason.NETWORK_ERROR)
            return False
        
        self.buffer += data
        
        while len(self.buffer) > 0:
            if self.buffer.startswith('ln='):
                tmp = self.buffer.index('\0')
                l = int(self.buffer[3:tmp])
                if l+tmp > len(self.buffer):
                    break    # wait for data
                self.buffer = self.buffer[tmp+1:]
                
                temp = self.buffer[:l]
                while len(temp) > 0:
                    tmp = temp.index('\0')
                    cid = int(temp[:tmp])
                    if cid == Server.BINARY.id:
                        self._parse_binary(temp[tmp+1:])
                        break
                    end = temp.find('\2')
                    if end == -1:
                        end = len(temp)
                    if end > 0:
                        self._parse_command(temp[:end])
                    temp = temp[end+1:]
                
                self.buffer = self.buffer[l:]
            else:
                #TODO
                logger.error("invalid start of message")
                i = self.buffer.find('ln=')
                if i >= 0:
                    self.buffer = self.buffer[i:]
                else:
                    self.buffer = ""
                    return True
        return True
           
        
    def _close(self):
        logger.info("CLOSING")
        if self.sock:
            self.sock.close()
        self.waiting_for = None
        self.roster = None
        self.queue = Queue()
        
      
                
    def _parse_binary(self, data):
        i = data.index('\0')
        response = build_response(data[:1].split('\1'))
        
        data = data[i+1:]
        data = BinaryStream(self, data)
        while data:
            cmd, l = data.read('BI')
            command = Binary.byid(cmd)
            logger.info("binary command %r of length %d" % (command, l))
            
            stream = BinaryStream(self, data.read_bytes(l))
            message = ServerMessage(command, response, stream)
            
            if self.waiting_for is not None and isinstance(self.waiting_for, BinaryMessage):
                try:
                    handled = self.waiting_for.received(message)
                except Exception, e:
                    logger.exception(e)
                    self.waiting_for = None
                    return
                
                if handled:
                    self.waiting_for = None
                    return
                
            if command == Binary.SPLASH:
                self._parse_splash(message)
            elif command == Binary.FILEDESC:
                self._parse_filedesc(message)
            else:
                logger.info("Unknown command: %s" % command)
                
            break # TODO: might remain with '\2', more binary data, or even normal data?
            
    
        
    def _parse_command(self, command):
        tree = self.create_tree(command)
        cmd_id = int(tree[0][0])
        response = build_response(tree[1])
        tree = tree[2:]
        cmd = Client.byid(cmd_id)    # First try client command - response
        
        message = ServerMessage(cmd, response, tree)
        
        logger.info("~ received ~ %d:%s/%s ~ %s ~ %s" % (cmd_id, cmd, Server.byid(cmd_id), response, tree))
        
        if self.waiting_for is not None:
            try:
                handled = self.waiting_for.received(message)
            except Exception, e:
                logger.exception(e)
                self.waiting_for = None
                return
            
            if handled:
                self.waiting_for = None
                return
            
        cmd = Server.byid(cmd_id)    # Now try server command
        message.cmd = cmd
        try:
            if cmd == Server.MESSAGE:
                self._r_message(message)
            elif cmd == Server.LOGOUT:
                self._r_logout(message)
            elif cmd == Server.PRESENCE:
                self._r_presence(message)
            elif cmd == Server.INVITE_RECEIVED:
                self._r_invite(message)
            else:
                logger.info("unknown command")
        except Exception, e:
            logger.exception(e)
            self.listeners.error("Error processing command", e)
    
        
    def write_once(self):
        # Loop until the queue is empty, or until we are waiting for a command
        while True:
            if self.queue.empty():
                return False
            if self.waiting_for is not None:
                logger.info("Still waiting for %s, not sending" % self.waiting_for)
                sent_at = self.waiting_for.sent_at
                if time.time() - sent_at > self.response_timeout:
                    logger.error("Timed out: %r" % self.waiting_for)
                    self.waiting_for.timeout()
                    self.waiting_for = None
                else:
                    gobject.timeout_add(500, self.write_once)
                    return False
        
            
            if self.status not in [Status.ACTIVE, Status.AUTHENTICATING, Status.DISCONNECTING]:
                logger.error("Not in a state to send data: %r" % (self.status))
                return False
            
            try:
                message = self.queue.get(block=False)
            except Empty:
                return False
            
            try:
                message.send(self.sock)
                if message.should_wait():
                    self.waiting_for = message
                    message.sent_at = time.time()
            except Exception, e:
                logger.exception(e)
                self._close()
                if self.status != Status.DISCONNECTED:
                    self._set_status(Status.DISCONNECTED, StatusChangeReason.NETWORK_ERROR)
            
                
            self.queue.task_done()
      
    
    def _connect(self):
        """ Connect to the server. """
        
        logger.info("Connecting to: %s:%d" % (self.host, self.port))
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.connect((self.host,self.port))
        #self.sock.setblocking(0)
    
    def create_tree(self, data):
        """ Parse a command. """
        result = []
        for a in data.split('\0'):
            sub = []
            for b in a.split('\1'):
                sub.append(self.from_mxit(b))
            result.append(sub)
        return result
        #return map(lambda s: s.split('\1'), data.split('\0'))

    
class Response:
    def __init__(self, code, message=None):
        self.code = code
        self.message = message
        
    def __str__(self):
        return "%d: %s" % (self.code, self.message)
    
    def __repr__(self):
        return "<Reponse %s>" % str(self)
        
def build_response(branch):
    code = int(branch[0])
    msg = None
    if len(branch) > 1:
        msg = branch[1]
    return Response(code, msg)

def readable(data):
    return repr(data)


