#!/usr/bin/python3
# -*- coding: UTF-8 -*- 

# XMPPD :: eXtensible Messaging and Presence Protocol Daemon

# Copyright (C) 2005 Kristopher Tate / BlueBridge Technologies Group, Inc.
# Copyright (C) 2004 Alexey Nezhdanov
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"XMPPD :: eXtensible Messaging and Presence Protocol Daemon"

__author__    = "Alexey Nezhdanov <snakeru@gmail.com>, Kristopher Tate <kris@bbridgetech.com>"
__version__   = "0.4-pre1"
__copyright__ = "Copyright (C) 2005 BlueBridge Technologies Group, Inc., 2004,2009 Alexey Nezhdanov"
__license__   = "GPL2+"

from optparse import OptionParser

parser = OptionParser(usage="%prog [options] [--hostname HOST] [-s host[:ip]]",version="%%prog %s"%__version__)
parser.add_option("-p", "--psyco",
                action="store_true", dest="enable_psyco",
                help="Enable PsyCo")

parser.add_option("--nofallback",
                action="store_true", dest="disable_fallback",
                help="Disables fallback support (Upon a major error, the server will not try to restart itself.)")

parser.add_option("-d", "--debug",
                action="store_true", dest="enable_debug",
                help="Enables debug messaging to console")

parser.add_option("--hostname", metavar="HOST", dest="hostname",
                    help="Used to explicitly set the hostname or IP of this daemon.")

parser.add_option('-s',"--socker", metavar="host[:ip]", dest="socker_info",
                    help="Enables, and connects to the host:ip " \
                    "of a socker(tm) socket multiplexor. [EXPERIMENTAL]")


parser.add_option("-i",
                action="store_true", dest="enable_interactive",
                help="Enables Interactive mode, allowing a console user to interactively edit the server in realtime.")

(cmd_options, cmd_args) = parser.parse_args()

if cmd_options.enable_psyco == True:
    if globals()['cmd_options'].enable_debug == True: print("Starting PsyCo...")
    try:
        import psyco
        psyco.log()
        psyco.full()
        if globals()['cmd_options'].enable_debug == True: print("PsyCo is loaded.")
    except:
        if globals()['cmd_options'].enable_debug == True: print("ERR Loading PsyCo!")

import xmpp
from xmpp import *
import traceback
import _thread
import _thread as thread
import socket,select,random,os,sys,errno,time,threading

if globals()['cmd_options'].socker_info != None: import xmlrpclib

select_enabled = False
try:
    import event # Do we have lib event???
except:
    select_enabled = True # If not, we'll have to just use the old select :/

SERVER_MOTD = "Hello, I'm Help Desk. Type 'menu' for help."

globals()['PORT_5222'] = 5222
globals()['PORT_5223'] = 5223
globals()['PORT_5269'] = 5269

SOCKER_TGUID = 'BBTECH_XMPPD' # CHANGE THIS IF YOU ARE TO USE SOCKER!

#Temp lang stuff
DEFAULT_LANG = 'en'
LANG_LIST=[]

"""
_socket_state live/dead
_session_state   no/in-process/yes
_stream_state not-opened/opened/closing/closed
"""
# Transport-level flags
SOCKET_UNCONNECTED  = 0
SOCKET_ALIVE        = 1
SOCKET_DEAD         = 2
# XML-level flags
STREAM__NOT_OPENED  = 1
STREAM__OPENED      = 2
STREAM__CLOSING     = 3
STREAM__CLOSED      = 4
# XMPP-session flags
SESSION_NOT_AUTHED  = 1
SESSION_AUTHED      = 2
SESSION_BOUND       = 3
SESSION_OPENED      = 4

class fake_select:
    def __init__(self): 
        ## poll flags
        self.POLLIN  = 0x0001
        self.POLLOUT = 0x0004
        self.POLLERR = 0x0008

        ## synonyms
        self.POLLNORM = self.POLLIN
        self.POLLPRI = self.POLLIN
        self.POLLRDNORM = self.POLLIN
        self.POLLRDBAND = self.POLLIN
        self.POLLWRNORM = self.POLLOUT
        self.POLLWRBAND = self.POLLOUT

        ## ignored
        self.POLLHUP = 0x0010
        self.POLLNVAL = 0x0020
    class poll:
        def __init__(self): 
            ## poll flags
            self.POLLIN  = 0x0001
            self.POLLOUT = 0x0004
            self.POLLERR = 0x0008

            ## synonyms
            self.POLLNORM = self.POLLIN
            self.POLLPRI = self.POLLIN
            self.POLLRDNORM = self.POLLIN
            self.POLLRDBAND = self.POLLIN
            self.POLLWRNORM = self.POLLOUT
            self.POLLWRBAND = self.POLLOUT

            ## ignored
            self.POLLHUP = 0x0010
            self.POLLNVAL = 0x0020
            self._registered = {}

        def register(self,fd,eventmask=None): 
            try:
                self._registered[fd.fileno()] = {'fd':fd,'mask':eventmask}
                return True
            except:
                return False

        def unregister(self,fd):
            try:
                del self._registered[fd.fileno()]
                return True
            except:
                return False

        def poll(self,timeout=None):

            data = {}
            poll = {'in':[],'out':[],'err':[]}
            out = []
            for x,y in self._registered.iteritems():
                if y['mask']&self.POLLIN == self.POLLIN: poll['in'] += [y['fd']]
                if y['mask']&self.POLLOUT == self.POLLOUT: poll['out'] += [y['fd']]
                if y['mask']&self.POLLERR == self.POLLERR: poll['err'] += [y['fd']]
            if timeout < 1 or timeout == None:
                pi,po,pe = select.select(poll['in'],poll['out'],poll['err'])
            else:
                pi,po,pe = select.select(poll['in'],poll['out'],poll['err'],timeout/1000.0)

            for x in poll['in']:
                if x in pi:
                    if x.fileno() in data:
                        data[x.fileno()]['mask'] = data[x.fileno()]['mask'] | self.POLLIN
                    else:
                        data[x.fileno()] = {'fd':x,'mask':self.POLLIN}

            for x in poll['out']:
                if x in po:
                    if x.fileno() in data:
                        data[x.fileno()]['mask'] = data[x.fileno()]['mask'] | self.POLLOUT
                    else:
                        data[x.fileno()] = {'fd':x,'mask':self.POLLOUT}

            for x in poll['err']:
                if x in pe:
                    if x.fileno() in data:
                        data[x.fileno()]['mask'] = data[x.fileno()]['mask'] | self.POLLERR
                    else:
                        data[x.fileno()] = {'fd':x,'mask':self.POLLERR}

            for k,d in data.iteritems():
                out += [(k,d['mask'])]
            return out

#Import all of the localization files
import locale_kris
LANG_LIST += [locale_kris.en_server_localized_strings,locale_kris.fr_server_localized_strings,locale_kris.ja_server_localized_strings]
#for m in os.listdir('locale'):
#    if m[:2]=='__' or m[-3:]!='.py': continue
#    execfile(os.getcwd() + '/locale/' + m[:-3] + '.py')

class localizer:
    def __init__(self,lang=None):
        global DEFAULT_LANG
        self._default = DEFAULT_LANG
        if lang == None or type(lang) != type(''):
            self._lang = DEFAULT_LANG
        else:
            self._lang = lang

    def set_lang(self,lang):
        self._lang = lang
        return True

    def localize(self,val,lang=None):
        if lang == None or lang not in val:
            lang = self._lang
        if lang not in val and self._default in val:
            lang = self._default

        try:
            return val[lang]
        except:
            if len(val.keys()) > 0:
                return val[val.keys()[0]] 
            else:
                return ''

    def build_localeset(self,records):
        for record in records.split('\n')[1:]:
            var,code,text=record.split(' -- ')
            name=var.upper().replace('-','_')
            if globals()['cmd_options'].enable_debug == True: print('adding ' + name + '::' + code)
            if name in globals():
                globals()[name].update({code:text})
            else:
                globals()[name] = {code:text}
        del var,code,text

class Session:
    def __init__(self,socket,server,xmlns,peer=None):
        self.xmlns=xmlns
        if peer:
            self.TYP='client'
            self.peer=peer
            self._socket_state=SOCKET_UNCONNECTED
        else:
            self.TYP='server'
            self.peer=None
            self._socket_state=SOCKET_ALIVE
            server.num_servers += 1
        self._sock=socket
        self._send=socket.send
        self._recv=socket.recv
        self._registered=0
        self.trusted=0
        self.conn_since = time.time()
        self.last_seen = time.time()
        self.isAdmin = False
        
        self.Dispatcher=server.Dispatcher
        self.DBG_LINE='session'
        self.DEBUG=server.Dispatcher.DEBUG
        self._expected={}
        self._owner=server
        if self.TYP=='server': self.ID=str(random.random())[2:]
        else: self.ID=None

        self.sendbuffer=''
        self.lib_event = None
        self._stream_pos_queued=None
        self._stream_pos_sent=0
        self.deliver_key_queue=[]
        self.deliver_queue_map={}
        self.stanza_queue=[]

        self._session_state=SESSION_NOT_AUTHED
        self.waiting_features=[]
        for feature in [NS_TLS,NS_SASL,NS_BIND,NS_SESSION]:
            if feature in server.features: self.waiting_features.append(feature)
        self.features=[]
        self.feature_in_process=None
        self.slave_session=None
        self.StartStream()

    def StartStream(self):
        self._stream_state=STREAM__NOT_OPENED
        self.Stream=simplexml.NodeBuilder()
        self.Stream._dispatch_depth=2
        self.Stream.dispatch=self.dispatch
        self.Parse=self.Stream.Parse
        self.Stream.stream_footer_received=self._stream_close
        if self.TYP=='client':
            self.Stream.stream_header_received=self._catch_stream_id
            self._stream_open()
        else:
            self.Stream.stream_header_received=self._stream_open

    def receive(self):
        """Reads all pending incoming data. Raises IOError on disconnect."""
        try: received = self._recv(10240)
        except: received = ''

        if len(received): # length of 0 means disconnect
            self.DEBUG(repr(self._sock.fileno())+' '+received,'got')
            self.last_seen = time.time()
        else:
            self.DEBUG(self._owner._l(SESSION_RECEIVE_ERROR),'error')
            self.set_socket_state(SOCKET_DEAD)
            raise IOError("Peer disconnected")
        return received

    def send(self,chunk):
        try:
            if isinstance(chunk,Node): chunk = unicode(chunk).encode('utf-8')
            elif type(chunk)==type(''): chunk = chunk.encode('utf-8')
            #self.enqueue(chunk)
        except:
            pass
        self.enqueue(chunk)

    def enqueue(self,stanza):
        """ Takes Protocol instance as argument. """
        self._owner.num_messages += 1
        if isinstance(stanza,Protocol):
            self.stanza_queue.append(stanza)
        else: self.sendbuffer+=stanza
        if self._socket_state>=SOCKET_ALIVE: self.push_queue()

    def push_queue(self,failreason=ERR_RECIPIENT_UNAVAILABLE):

        if self._stream_state>=STREAM__CLOSED or self._socket_state>=SOCKET_DEAD: # the stream failed. Return all stanzas that are still waiting for delivery.
            self._owner.deactivatesession(self)
            self.trusted=1
            for key in self.deliver_key_queue:                            # Not sure. May be I
                self.dispatch(Error(self.deliver_queue_map[key],failreason)) # should simply re-dispatch it?
            for stanza in self.stanza_queue:                              # But such action can invoke
                self.dispatch(Error(stanza,failreason))                   # Infinite loops in case of S2S connection...
            self.deliver_queue_map,self.deliver_key_queue,self.stanza_queue={},[],[]
            return
        elif self._session_state>=SESSION_AUTHED:       # FIXME! 
            #### LOCK_QUEUE
            for stanza in self.stanza_queue:
                txt=stanza.__str__().encode('utf-8')
                self.sendbuffer+=txt
                self._stream_pos_queued+=len(txt)       # should be re-evaluated for SSL connection.
                self.deliver_queue_map[self._stream_pos_queued]=stanza     # position of the stream when stanza will be successfully and fully sent
                self.deliver_key_queue.append(self._stream_pos_queued)
            self.stanza_queue=[]
            #### UNLOCK_QUEUE
        
        if self.sendbuffer and select.select([],[self._sock],[])[1]:
            try:
                # LOCK_QUEUE
                sent=self._send(self.sendbuffer)   
            except Exception as err:
                if globals()['cmd_options'].enable_debug == True: print('Attempting to kill %i!!!\n%s'%(self._sock.fileno(),err))
                # UNLOCK_QUEUE
                self.set_socket_state(SOCKET_DEAD)
                self.DEBUG(self._owner._l(SESSION_SEND_ERROR),'error')
                return self.terminate_stream()
            self.DEBUG(repr(self._sock.fileno())+' '+self.sendbuffer[:sent],'sent')
            self._stream_pos_sent+=sent
            self.sendbuffer=self.sendbuffer[sent:]
            self._stream_pos_delivered=self._stream_pos_sent            # Should be acquired from socket somehow. Take SSL into account.
            while self.deliver_key_queue and self._stream_pos_delivered>self.deliver_key_queue[0]:
                del self.deliver_queue_map[self.deliver_key_queue[0]]
                self.deliver_key_queue.remove(self.deliver_key_queue[0])
            # UNLOCK_QUEUE
        """
        elif self.lib_event == None:
            if globals()['cmd_options'].enable_debug == True: print('starting-up libevent write-event for %i'%self._sock.fileno())
            self.lib_event = event.write(self._sock,self.libevent_write)
            self.lib_event.add()
        else:
            self.lib_event.add()"""
            


    def libevent_write(self):
        if self.sendbuffer:
            
            try:
                # LOCK_QUEUE
                sent=self._send(self.sendbuffer)   
            except Exception as err:
                if globals()['cmd_options'].enable_debug == True: print('Attempting to kill %i!!!\n%s'%(self._sock.fileno(),err))
                # UNLOCK_QUEUE
                self.set_socket_state(SOCKET_DEAD)
                self.DEBUG(self._owner._l(SESSION_SEND_ERROR),'error')
                return self.terminate_stream()
            self.DEBUG(repr(self._sock.fileno())+' '+self.sendbuffer[:sent],'sent')
            self._stream_pos_sent+=sent
            self.sendbuffer=self.sendbuffer[sent:]
            self._stream_pos_delivered=self._stream_pos_sent            # Should be acquired from socket somehow. Take SSL into account.
            while self.deliver_key_queue and self._stream_pos_delivered>self.deliver_key_queue[0]:
                del self.deliver_queue_map[self.deliver_key_queue[0]]
                self.deliver_key_queue.remove(self.deliver_key_queue[0])
            # UNLOCK_QUEUE

    def dispatch(self,stanza):
        if self._stream_state==STREAM__OPENED:                  # if the server really should reject all stanzas after he is closed stream (himeself)?
            self.DEBUG(stanza.__str__(),'dispatch')
            return self.Dispatcher.dispatch(stanza,self)

    def fileno(self): return self._sock.fileno()

    def _catch_stream_id(self,ns=None,tag='stream',attrs={}):
        if id not in attrs or not attrs['id']:
            return self.terminate_stream(STREAM_INVALID_XML)
        self.ID=attrs['id']
        if 'version' not in attrs: self._owner.Dialback(self)

    def _stream_open(self,ns=None,tag='stream',attrs={}):
        text='<?xml version="1.0" encoding="utf-8"?>\n<stream:stream'
        if self.TYP=='client':
            text+=' to="%s"'%self.peer
        else:
            text+=' id="%s"'%self.ID
            if 'to' not in attrs: text+=' from="%s"'%self._owner.servernames[0]
            else: text+=' from="%s"'%attrs['to']
        if 'xml:lang' in attrs: text+=' xml:lang="%s"'%attrs['xml:lang']
        if self.xmlns: xmlns=self.xmlns
        else: xmlns=NS_SERVER
        text+=' xmlns:db="%s" xmlns:stream="%s" xmlns="%s"'%(NS_DIALBACK,NS_STREAMS,xmlns)
        if 'version' in attrs or self.TYP=='client': text+=' version="1.0"'
        self.send(text+'>')
        self.set_stream_state(STREAM__OPENED)
        if self.TYP=='client': return
        if tag!='stream': return self.terminate_stream(STREAM_INVALID_XML)
        if ns!=NS_STREAMS: return self.terminate_stream(STREAM_INVALID_NAMESPACE)
        if self.Stream.xmlns!=self.xmlns: return self.terminate_stream(STREAM_BAD_NAMESPACE_PREFIX)
        if 'to' not in attrs: return self.terminate_stream(STREAM_IMPROPER_ADDRESSING)
        if attrs['to'] not in self._owner.servernames: return self.terminate_stream(STREAM_HOST_UNKNOWN)
        self.ourname=attrs['to'].lower()
        if self.TYP=='server' and 'version' in attrs: self.send_features()

    def send_features(self):
        features=Node('stream:features')
        if NS_TLS in self.waiting_features:
            features.T.starttls.setNamespace(NS_TLS)
            features.T.starttls.T.required
        if NS_SASL in self.waiting_features:
            features.T.mechanisms.setNamespace(NS_SASL)
            for mec in self._owner.SASL.mechanisms:
                features.T.mechanisms.NT.mechanism=mec
        else:
            if NS_BIND in self.waiting_features: features.T.bind.setNamespace(NS_BIND)
            if NS_SESSION in self.waiting_features: features.T.session.setNamespace(NS_SESSION)
        self.send(features)

    def getResource(self):
        jid=self.peer
        try: barejid,resource=jid.split('/')
        except: return None
        return resource
            
    def getRoster(self):
        split_jid = self.getSplitJID()
        return self._owner.DB.get(split_jid[1],split_jid[0],'roster')

    def getGroups(self):
        split_jid = self.getSplitJID()
        return self._owner.DB.get(split_jid[1],split_jid[0],'groups')

    def getName(self):
        split_jid = self.getSplitJID()
        name = self._owner.DB.get(split_jid[1],split_jid[0],'name')
        if name == None: name = '%s@%s'%split_jid[0:2]
        return name
        
    def getSplitJID(self):
        return self._owner.tool_split_jid(self.peer)

    def getBareJID(self):
        return '%s@%s'%self.getSplitJID()[0:2]

    def getKarma(self):
        split_jid = self.getSplitJID()
        if split_jid != None:
            return self._owner.DB.get_store(split_jid[1],split_jid[0],'karma')
        else:
            return None

    def updateKarma(self,karma):
        split_jid = self.getSplitJID()
        if split_jid != None:
            return self._owner.DB.store(split_jid[1],split_jid[0],karma,'karma')
        else:
            return None
            
    def feature(self,feature):
        if feature not in self.features: self.features.append(feature)
        self.unfeature(feature)

    def unfeature(self,feature):
        if feature in self.waiting_features: self.waiting_features.remove(feature)

    def _stream_close(self,unregister=1):
        if self._stream_state>=STREAM__CLOSED: return
        self.set_stream_state(STREAM__CLOSING)
        self.send('</stream:stream>')
        self.set_stream_state(STREAM__CLOSED)
        self.push_queue()       # decompose queue really since STREAM__CLOSED
        if unregister: self._owner.unregistersession(self)
        if self.lib_event != None: self.lib_event.delete()
        self._destroy_socket()

    def terminate_stream(self,error=None,unregister=1):
        if self._stream_state>=STREAM__CLOSING: return
        if self._stream_state<STREAM__OPENED:
            self.set_stream_state(STREAM__CLOSING)
            self._stream_open()
        else:
            self.set_stream_state(STREAM__CLOSING)
            p=Presence(typ='unavailable')
            p.setNamespace(NS_CLIENT)
            self.Dispatcher.dispatch(p,self)
        if error:
            if isinstance(error,Node): self.send(error)
            else: self.send(ErrorNode(error))
        self._stream_close(unregister=unregister)
        if self.slave_session:
            self.slave_session.terminate_stream(STREAM_REMOTE_CONNECTION_FAILED)

    def _destroy_socket(self):
        """ breaking cyclic dependancy to let python's GC free memory just now """
        self.Stream.dispatch=None
        self.Stream.stream_footer_received=None
        self.Stream.stream_header_received=None
        self.Stream.destroy()
        self._sock.close()
        self.set_socket_state(SOCKET_DEAD)

    def start_feature(self,f):
        if self.feature_in_process: raise "Starting feature %s over %s !"%(f,self.feature_in_process)
        self.feature_in_process=f
    def stop_feature(self,f):
        if self.feature_in_process!=f: self.DEBUG("Stopping feature %s instead of %s !"%(f,self.feature_in_process),'info')
        self.feature_in_process=None
    def set_socket_state(self,newstate):
        if self._socket_state<newstate: self._socket_state=newstate
    def set_session_state(self,newstate):
        if self._session_state<newstate:
            if self._session_state<SESSION_AUTHED and \
               newstate>=SESSION_AUTHED: self._stream_pos_queued=self._stream_pos_sent
            self._session_state=newstate
            split_jid = self.getSplitJID()
            if split_jid != None and split_jid[0] in self._owner.administrators[self.ourname]:
                self.isAdmin = True
                self.DEBUG(self._owner._l(SESSION_ADMIN_SET)%str(split_jid[0]),'info')
#            if newstate==SESSION_OPENED: self.enqueue(Message(self.peer,SERVER_MOTD,frm=self.ourname))     # Remove in prod. quality server
    def set_stream_state(self,newstate):
        if self._stream_state<newstate: self._stream_state=newstate

class Socker_client:
    def __init__(self,socker_host,tguid,sguid=None):
        self._proxy = xmlrpclib.ServerProxy('http://%s'%socker_host)       

        try: #See if the Socker server will say hello...
            ok_res = self._proxy.hello({})
            if ok_res['code'] == 1: self.conn_okay = True
        except:
            self.conn_okay = False

        self._tguid = tguid
        if globals()['cmd_options'].hostname != None:
            if globals()['cmd_options'].enable_debug == True: print("[SOCKER] hostname set to <%s>" % globals()['cmd_options'].hostname)
            self._hostname = str(globals()['cmd_options'].hostname)
        else:
            self._hostname = None
        
        if sguid == None:
            self._sguid = self.get_uuid()
        else:
            self._sguid = sguid
        
        self._registered = []
    
    def get_uuid(self):
        if self.conn_okay == True:
            return self._proxy.uuidgen({})
        else:
            return None

    def get_hostname(self):
        if self.conn_okay == True:
            res = self._proxy.hostname({})
            if 'hostname' in res:
                self._hostname = res['hostname']
                return res['hostname']
            else:
                return None
        else:
            return None

    def get_sguid(self):
        return self._sguid

    def get_tguid(self):
        return self._tguid

    def add_port(self,outside_port,host,port,options=None):
        if globals()['cmd_options'].enable_debug == True: print("[SOCKER] attempting to add route to Socker [%s]"%str((outside_port,host,port,options)))
        if host == None and self._hostname != None:
            host = self._hostname
        elif host == None and self._hostname == None:
            host = self.get_hostname()

        inpt = {'outside_port':outside_port,'type_guid':self._tguid+'_p%s'%str(outside_port),'server_guid':self._sguid,'server_host':host,'server_port':port}
        if options != None: inpt.update(options)

        res = self._proxy.add(inpt) #Send request to Socker
        if res['code'] != 1:
            return None
        else:
            self._registered += [res]
            return res

    def destroy(self):
        for registered in self._registered:
            res = self._proxy.delete({'handle':registered['handle'],'type_guid':self._tguid+'_p%s'%str(registered['outside_port']),'server_guid':self._sguid}) #Send request to Socker

        if res['code'] != 1:
            return None
        else:
            self._registered = []
            return res

class Server:
    def __init__(self,debug=['always'],under_restart=False,debug_file=sys.stdout):
#        threading.Thread.__init__(self)
        self.defaultNamespace = NS_CLIENT
        #Load localizer as _l
        self.l = localizer('ja')
        self._l = self.l.localize
        for x in LANG_LIST:
            self.l.build_localeset(x)

        self.sockets={}
        self.leventobjs={}
        if select_enabled and not getattr(select,'poll',None):
            self.sockpoll = fake_select.poll()
        elif select_enabled:
            self.sockpoll=select.poll()
        self.ID=str(random.random())[2:]

        self._DEBUG=Debug.Debug(debug,debug_file)
        self.DEBUG=self._DEBUG.Show
        self.debug_flags=self._DEBUG.debug_flags
        self.debug_flags.append('session')
        self.debug_flags.append('dispatcher')
        self.debug_flags.append('server')

        self.SESS_LOCK=thread.allocate_lock()
        self.Dispatcher=dispatcher.Dispatcher()
        self.Dispatcher._owner=self
        self.Dispatcher._init()

        #stats
        self.up_since = time.time()
        self.num_messages = 0
        self.num_servers = 0

        self.features=[]
        import modules
        if under_restart == True:
            reload(modules)
        for addon in modules.addons:
            if issubclass(addon,PlugIn):
                if addon().__class__.__name__ in self.__dict__ and under_restart:
#                    self.DEBUG('server','Plugging-out?','info')

                    self.DEBUG('server','Plugging %s out of %s.'%(addon(),self),'stop')
                    if addon().DBG_LINE in self.debug_flags:
                        self.debug_flags.remove(addon().DBG_LINE)
                    if getattr(addon(),'_exported_methods',None) != None:
                        for method in addon()._exported_methods: del self.__dict__[method.__name__]
                    if getattr(addon(),'_old_owners_methods',None) != None:
                        for method in addon()._old_owners_methods: self.__dict__[method.__name__]=method
                    del self.__dict__[addon().__class__.__name__]
                    if 'plugout' in addon().__class__.__dict__: return addon().plugout()

                    addon().PlugIn(self)
                else:
                    addon().PlugIn(self)
            else: self.__dict__[addon.__class__.__name__]=addon()
            self.feature(addon.NS)
        self.routes={}
        self._socker = None
        if globals()['cmd_options'].socker_info:
            self._socker = Socker_client(globals()['cmd_options'].socker_info,globals()['SOCKER_TGUID'])

        if self._socker != None and self._socker.conn_okay == True:
            if globals()['cmd_options'].enable_debug:
                print("[SOCKER] Socker(tm) support is enabled.")
                print("[SOCKER] Randomizing incoming connection ports.")

            #Generate port map
            guide = [[globals()['PORT_5222'],self.pick_rand(),'5222'],[globals()['PORT_5223'],self.pick_rand(),'5223'],[globals()['PORT_5269'],self.pick_rand(),'5269']]

            port_map = {}
            for x in guide:
                port_map[str(x[0])] = x[1]
                globals()['PORT_%s'%x[2]] = x[1]
        
            for port, new_port in port_map.iteritems():
                    sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(('', new_port))
                    sock.listen(1)
                    self.registersession(sock)
                    info = self._socker.add_port(int(port),None,new_port,{'conn_max':500})
                    if info == None: 
                        self._socker.destroy()
                        raise Exception


        else:
            if globals()['cmd_options'].enable_debug == True and globals()['cmd_options'].socker_info != None: print("[SOCKER] Socker(tm) support could not be enabled. Please make sure that the Socker server is active.")
            self._socker = None
            for port in [globals()['PORT_5222'],globals()['PORT_5223'],globals()['PORT_5269']]:
                sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('', port))
                sock.listen(1)
                self.registersession(sock)

    def tool_split_jid(self,jid):
        "Returns tuple of id,server,resource"
        try: id,extras=jid.split('@')
        except: return None
        try: server,resource=extras.split('/')
        except: return (id,extras)
        return (id,server,resource)

    def feature(self,feature):
        if feature and feature not in self.features: self.features.append(feature)

    def unfeature(self,feature):
        if feature and feature in self.features: self.features.remove(feature)

    def registersession(self,s):
        self.SESS_LOCK.acquire()
        if isinstance(s,Session):
            if s._registered:
                self.SESS_LOCK.release()
                if self._DEBUG.active: raise "Twice session Registration!"
                else: return
            s._registered=1
        reg_method = ''
        self.sockets[s.fileno()]=s
        if select_enabled:
            reg_method = 'select'
            self.sockpoll.register(s,1 | 2 | 8)
        elif 'event' in globals().keys():
            reg_method = 'libevent'
            self.leventobjs[s.fileno()]= event.event(self.libevent_read_callback, handle = s, evtype = event.EV_TIMEOUT | event.EV_READ | event.EV_PERSIST)
            if self.leventobjs[s.fileno()] != None:
                self.leventobjs[s.fileno()].add()
        if isinstance(self._socker,Socker_client):
            socker_notice = "->[SOCKER(TM)]"
        else:
            socker_notice = ''
        self.DEBUG('server',self._l(SERVER_NODE_REGISTERED)%{'fileno':s.fileno(),'raw':s,'method':reg_method,'socker_notice':socker_notice})
        self.SESS_LOCK.release()

    def unregistersession(self,s):
        self.SESS_LOCK.acquire()
        if isinstance(s,Session):
            if not s._registered:
                p=Presence(typ='unavailable')
                p.setNamespace(NS_CLIENT)
                self.Dispatcher.dispatch(p,s)
                self.SESS_LOCK.release()
                if self._DEBUG.active: raise "Twice session UNregistration!"
                else: return
            s._registered=0
        if getattr(self,'sockpoll',None) != None:
            self.sockpoll.unregister(s)
        elif s.fileno() in self.leventobjs and self.leventobjs[s.fileno()] != None:
            self.leventobjs[s.fileno()].delete() # Kill libevent event
            del self.leventobjs[s.fileno()]

        del self.sockets[s.fileno()] # Destroy the record
        self.DEBUG('server',self._l(SERVER_NODE_UNREGISTERED)%{'fileno':s.fileno(),'raw':s})
        self.SESS_LOCK.release()

    def activatesession(self,s,peer=None):
        if not peer: peer=s.peer
        alt_s=self.getsession(peer)
        if s==alt_s: return
        elif alt_s: self.deactivatesession(peer)
        self.routes[peer]=s

    def getsession(self, jid):
        try: return self.routes[jid]
        except KeyError: pass

    def deactivatesession(self, peer):
        s=self.getsession(peer)
        if peer in self.routes: del self.routes[peer]
        return s

    def run(self):
        global GLOBAL_TERMINATE
        if 'event' in globals(): event.signal(2,self._lib_out).add()
        if select_enabled:
            while GLOBAL_TERMINATE == False:
                self.select_handle()
        elif 'event' in globals(): event.dispatch()

    def libevent_read_callback(self, ev, fd, evtype, pipe):
        sock = self.sockets[fd.fileno()]
        if isinstance(sock,Session):
            sess=sock
            try:
                data=sess.receive()
            except IOError: # client closed the connection
                sess.terminate_stream()
                data=''
            if data:
                try:
                    sess.Parse(data)
                except simplexml.xml.parsers.expat.ExpatError:
                    sess.terminate_stream(STREAM_XML_NOT_WELL_FORMED)
            if time.time() - sess.last_seen >= 60.0:
                sess.terminate_stream()
        elif isinstance(sock,socket.socket):
            conn, addr = sock.accept()
            host,port=sock.getsockname()
            if port in [globals()['PORT_5222'],globals()['PORT_5223']]:
                sess=Session(conn,self,NS_CLIENT)
#                    self.DEBUG('server','%s:%s is a client!'%(host,port),'info')
            else:
#                    self.DEBUG('server','%s:%s is a server!'%(host,port),'info')
                sess=Session(conn,self,NS_SERVER)
            self.registersession(sess)
            if port==globals()['PORT_5223']: 
                self.TLS.startservertls(sess)
        else: raise "Unknown instance type: %s"%sock


    def select_handle(self):
        for fileno,ev in self.sockpoll.poll(1000):
            sock=self.sockets[fileno]
            if isinstance(sock,Session):
                sess=sock
                try:
                    data=sess.receive()
                except IOError: # client closed the connection
                    sess.terminate_stream()
                    data=''
                if data:
                    try:
                        sess.Parse(data)
                    except simplexml.xml.parsers.expat.ExpatError:
                        sess.terminate_stream(STREAM_XML_NOT_WELL_FORMED)
                if time.time() - sess.last_seen >= 60.0:
                    sess.terminate_stream()
            elif isinstance(sock,socket.socket):
                conn, addr = sock.accept()
                host,port=sock.getsockname()
                if port in [globals()['PORT_5222'],globals()['PORT_5223']]:
                    sess=Session(conn,self,NS_CLIENT)
#                    self.DEBUG('server','%s:%s is a client!'%(host,port),'info')
                else:
#                    self.DEBUG('server','%s:%s is a server!'%(host,port),'info')
                    sess=Session(conn,self,NS_SERVER)
                self.registersession(sess)
                if port==globals()['PORT_5223']: self.TLS.startservertls(sess)
            else: raise "Unknown instance type: %s"%sock

    def _lib_out(self):
        if isinstance(self._socker,Socker_client): self._socker.destroy()
        event.abort()
        self.DEBUG('server',self._l(SERVER_SHUTDOWN_MSG),'info')
        self.shutdown(STREAM_SYSTEM_SHUTDOWN)

    def shutdown(self,reason):
        global GLOBAL_TERMINATE
        GLOBAL_TERMINATE = True
        socklist=self.sockets.keys()
        for fileno in socklist:
            s=self.sockets[fileno]
            if isinstance(s,socket.socket):
                self.unregistersession(s)
                s.shutdown(2)
                s.close()
            elif isinstance(s,Session): s.terminate_stream(reason)

    def S2S(self,ourname,domain,slave_session=None):
        s=Session(socket.socket(socket.AF_INET, socket.SOCK_STREAM),self,NS_SERVER,domain)
        s.slave_session=slave_session
        s.ourname=ourname
        self.activatesession(s)
        thread.start_new_thread(self._connect_session,(s,domain))
        return s

    def _connect_session(self,session,domain):
        print(session.DEBUG(self._owner._l(SERVER-S2S-ATTEMPT-CONNECTION)%{'server':domain},'info'))
        try: session._sock.connect((domain,5269))
        except socket.error as err:
            print(session.DEBUG(self._l(SERVER_S2S_THREAD_ERROR)%err,'error'))
            self._owner.num_servers -= 1
            session.set_session_state(SESSION_BOUND)
            session.set_socket_state(SOCKET_DEAD)
            if err[0]==errno.ETIMEDOUT: failreason=ERR_REMOTE_SERVER_TIMEOUT
            elif err[0]==socket.EAI_NONAME: failreason=ERR_REMOTE_SERVER_NOT_FOUND
            else: failreason=ERR_UNDEFINED_CONDITION
            session.push_queue(failreason)
            session.terminate_stream(STREAM_REMOTE_CONNECTION_FAILED,unregister=0)
            return
        session.set_socket_state(SOCKET_ALIVE)
        session.push_queue()
        self.registersession(session)

    def Privacy(self,peer,stanza):
        self.DEBUG('server',self._l(SERVER_PVCY_ACTIVATED),'warn')
        template_input = {'jid_from':unicode(peer.peer).encode('utf-8'),'jid_to':unicode(stanza['to']).encode('utf-8')}
        split_jid=self.tool_split_jid(peer.peer)
        if split_jid == None: return
        self.DEBUG('server',self._l(SERVER_PVCY_ACCESS_CHECK)%template_input,'info')                     
           
        #Stanza Stuff
        to=stanza['to']
        if not to: return # Not for us.
        to_node=to.getNode()
        if not to_node: return # Yep, not for us.
        to_domain=to.getDomain()
        if to_domain in self.servernames and to_domain != to:
            bareto=to_node+'@'+to_domain
            name=stanza.getName()
            typ=stanza.getType()
            to_roster=self.DB.get(to_domain,to_node,'roster')
            
            if self.DB.get(to_domain,to_node,'anon_allow') == 'yes':
                anon_allow=True
            else:
                anon_allow=False
                
            to_working_roster_item=None
            #Session stuff
            roster=peer.getRoster()
            node = split_jid[0]
            domain = split_jid[1]
            resource = split_jid[2]

            if name=='presence':
                if stanza.getType() in ["subscribe", "subscribed", "unsubscribe", "unsubscribed"]:
                    self.DEBUG('server',self._l(SERVER_PVCY_ACCESS_CLEAR_ONEWAY_PRESENCE)%template_input,'info')
                    return

            if node+'@'+domain == bareto:
                self.DEBUG('server',self._l(SERVER_PVCY_ACCESS_CLEAR_UNLIMITED)%template_input,'info')
                return
            
            if to_roster != None:
                for x,y in to_roster.iteritems():
                    if x == node+'@'+domain:
                        to_working_roster_item = y
                        break;
            
            if to_working_roster_item == None and anon_allow==False:
                peer.send(Error(stanza,ERR_NOT_AUTHORIZED))
                self.DEBUG('server',self._l(SERVER_PVCY_ACCESS_NOTCLEAR_DOUBLEFALSE)%template_input,'error')
                raise NodeProcessed # Take the blue pill
            elif to_working_roster_item == None and anon_allow==True:
                to_working_roster_item = {}
                to_working_roster_item['subscription'] = 'none'
                        
            for z,a in roster.iteritems():
                if z == bareto:
                    if a['subscription']=='both' and 'subscription' in to_working_roster_item and to_working_roster_item['subscription']=='both':
                        self.DEBUG('server',self._l(SERVER_PVCY_ACCESS_CLEAR_BIDIRECTIONAL)%template_input,'info')
                        return
                    elif to_working_roster_item['subscription']=='from':
                        self.DEBUG('server',self._l(SERVER_PVCY_ACCESS_CLEAR_ONEWAY)%template_input,'info')
                        return
                    elif to_working_roster_item['subscription']=='to':
                        peer.send(Error(stanza,ERR_NOT_AUTHORIZED))
                        self.DEBUG('server',self._l(SERVER_PVCY_ACCESS_NOTCLEAR_MODETO)%template_input,'error')
                        raise NodeProcessed # Take the blue pill

            if anon_allow == True or str(to) in self.servernames:
                return
            else:
                peer.send(Error(stanza,ERR_NOT_AUTHORIZED))
                self.DEBUG('server',self._l(SERVER_PVCY_ACCESS_NOTCLEAR_FALSEANON)%template_input,'error')
                raise NodeProcessed # Take the blue pill
        return

    def Dialback(self,session):
        session.terminate_stream(STREAM_UNSUPPORTED_VERSION)

    def pick_rand(self):
        "return random int from 7000 to 8999 -- used for random port"
        import random
        return random.randrange(7000,8999)

def start_new_thread_fake(func,args):
    func(*args)

def testrun():
    thread.start_new_thread=start_new_thread_fake
    import modules
    modules.stream.thread.start_new_thread=start_new_thread_fake
    return Server()

class get_input(threading.Thread):
    def __init__(self,owner):
        self._owner = owner
        threading.Thread.__init__(self)
    def run(self):
        global GLOBAL_TERMINATE
        while GLOBAL_TERMINATE == False:
            the_input = raw_input("")
            if the_input == 'restart':
                self._owner.DEBUG('server','Stand-by; Restarting entire server!','info')
                self._owner.shutdown(STREAM_SYSTEM_SHUTDOWN)
                self._owner.DEBUG('server','Server has been shutdown, restarting NOW!','info')
                GLOBAL_TERMINATE = False
                self._owner.__init__(['always'],True)

            elif the_input == 'sys_debug':
                print(sys.exc_info())
                print(traceback.print_exc())
            elif the_input.split(' ')[0] == 'restart':

                import modules
                reload(modules)
                for addon in modules.addons:
                    if addon().__class__.__name__.lower() == the_input.split(' ')[1].lower():
                        if issubclass(addon,PlugIn):
                            if addon().__class__.__name__ in self._owner.__dict__:
            #                    self.DEBUG('server','Plugging-out?','info')

                                self._owner.DEBUG('server','Plugging %s out of %s.'%(addon(),s),'stop')
                                if addon().DBG_LINE in self._owner.debug_flags:
                                    self._owner.debug_flags.remove(addon().DBG_LINE)
                                if getattr(addon(),'_exported_methods',None) != None:
                                    for method in addon()._exported_methods: del self._owner.__dict__[method.__name__]
                                if getattr(addon(),'_old_owners_methods',None) != None:
                                    for method in addon()._old_owners_methods: self._owner.__dict__[method.__name__]=method
                                del self._owner.__dict__[addon().__class__.__name__]
                                if 'plugout' in addon().__class__.__dict__: addon().plugout()
                                self._owner.unfeature(addon.NS)

                                addon().PlugIn(s)
                            else:
                                addon().PlugIn(s)
                        else: self._owner.__dict__[addon.__class__.__name__]=addon()
                        self._owner.feature(addon.NS)

            elif the_input.split(' ')[0] == 'start':

                import modules
                reload(modules)
                for addon in modules.addons:
                    if addon().__class__.__name__.lower() == the_input.split(' ')[1].lower():
                        if issubclass(addon,PlugIn):
                            addon().PlugIn(s)
                        else: self._owner.__dict__[addon.__class__.__name__]=addon()
                        self._owner.feature(addon.NS)

            elif the_input.split(' ')[0] == 'stop':

                import modules
                reload(modules)
                for addon in modules.addons:
                    if addon().__class__.__name__.lower() == the_input.split(' ')[1].lower():
                        if issubclass(addon,PlugIn):
                            if addon().__class__.__name__ in self._owner.__dict__:
            #                    self.DEBUG('server','Plugging-out?','info')

                                self._owner.DEBUG('server','Plugging %s out of %s.'%(addon(),s),'stop')
                                if addon().DBG_LINE in self._owner.debug_flags:
                                    self._owner.debug_flags.remove(addon().DBG_LINE)
                                if getattr(addon(),'_exported_methods',None) != None:
                                    for method in addon()._exported_methods: del self._owner.__dict__[method.__name__]
                                if getattr(addon(),'_old_owners_methods',None) != None:
                                    for method in addon()._old_owners_methods: self._owner.__dict__[method.__name__]=method
                                del self._owner.__dict__[addon().__class__.__name__]
                                if 'plugout' in addon().__class__.__dict__: addon().plugout()
                            else:
                                self._owner.DEBUG('server','Error: Could not un-plug %s'%addon().__class__.__name__,'error')
                        else:
                            if getattr(addon(),'_exported_methods',None) != None:
                                for method in addon()._exported_methods: del self._owner.__dict__[method.__name__]
                            if getattr(addon(),'_old_owners_methods',None) != None:
                                for method in addon()._old_owners_methods: self._owner.__dict__[method.__name__]=method
                            del self._owner.__dict__[addon().__class__.__name__]
                            if 'plugout' in addon().__class__.__dict__: addon().plugout()
                        if addon().__class__.__name__ in self._owner.__dict__:
                            self._owner.DEBUG('server','Error: Could not un-plug %s'%addon().__class__.__name__,'error')
                        self._owner.unfeature(addon.NS)

            elif the_input == 'quit':
                GLOBAL_TERMINATE = True
                event.abort()
                break
            time.sleep(.01)


if __name__=='__main__':
    if 'event' in globals().keys(): event.init()
    debug_mode = None
    debug_file = sys.stdout
    if globals()['cmd_options'].enable_debug == True:
        debug_mode = ['always']
    else:
        debug_file = open('xmppd.log','w+')
    s=Server(debug_mode,False,debug_file)
    inpt_service = get_input(s)
    inpt_service.setDaemon(True)

    GLOBAL_TERMINATE = False
    if cmd_options.enable_interactive == True: inpt_service.start()
    while GLOBAL_TERMINATE == False:
        try:
            s.run()
#            s.DEBUG('server',s._l(SERVER_SHUTDOWN_MSG),'info')
#            s.shutdown(STREAM_SYSTEM_SHUTDOWN)
        except KeyboardInterrupt:
            s.DEBUG('server',s._l(SERVER_SHUTDOWN_MSG),'info')
            s.shutdown(STREAM_SYSTEM_SHUTDOWN)
        except:
            if 'event' in globals().keys(): event.abort()
            if globals()['cmd_options'].enable_debug == True:
                print('Check your traceback file, please!')
            tbfd = file('xmppd.traceback','a')
            tbfd.write(str('\nTRACEBACK REPORT FOR XMPPD for %s\n' + '='*55 + '\n')%time.strftime('%c'))
            #write traceback
            traceback.print_exc(None,tbfd)
            tbfd.close()
        if cmd_options.disable_fallback == True: GLOBAL_TERMINATE = True
