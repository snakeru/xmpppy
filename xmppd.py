#!/usr/bin/python
##
##   XMPP server
##
##   Copyright (C) 2004 Alexey "Snake" Nezhdanov
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

# $Id: xmppd.py,v 1.5 2004-10-03 17:45:34 snakeru Exp $

from xmpp import *
if __name__=='__main__':
    print "Firing up PsyCo"
    from psyco.classes import *
import socket,select,random,os,modules,thread
"""
_socket_state live/dead
_auth_state   no/in-process/yes
_stream_state not-opened/opened/closing/closed
"""
SOCKET_ALIVE        =1
SOCKET_DEAD         =2
SOCKET_UNREGISTERED =3
NOT_AUTHED =1
AUTHED     =2
BOUND      =3
STREAM_NOT_OPENED =1
STREAM_OPENED     =2
STREAM_CLOSING    =3
STREAM_CLOSED     =4

class Session:
    def __init__(self,socket,server,peer=None):
        host,port=socket.getsockname()
        self.xmlns=None
        if peer:
            self.TYP='client'
            self.peer=peer
        else:
            self.TYP='server'
            if port in [5222,5223]: self.xmlns=NS_CLIENT
            if port==5223: server.TLS.starttls(self)
            self.peer=None
        self._sock=socket
        self._send=socket.send
        self._recv=socket.recv
        self._socket_state=SOCKET_ALIVE

        self.Dispatcher=server.Dispatcher
        self.DBG_LINE='session'
        self.DEBUG=server.Dispatcher.DEBUG
        self._expected={}
        self._owner=server
        self.ID=`random.random()`[2:]
        self.StartStream()
        self._auth_state=NOT_AUTHED
        self.waiting_features=[]
        for feature in [NS_TLS,NS_SASL,NS_BIND,NS_SESSION]:
            if feature in server.features: self.waiting_features.append(feature)
        self.features=[]

    def StartStream(self):
        self._stream_state=STREAM_NOT_OPENED
        self.Stream=simplexml.NodeBuilder()
        self.Stream._dispatch_depth=2
        self.Stream.dispatch=self.dispatch
        self.Parse=self.Stream.Parse
        self.Stream.stream_footer_received=self._stream_close
        if self.TYP=='client': self._stream_open()
        else: self.Stream.stream_header_received=self._stream_open

    def receive(self):
        """Reads all pending incoming data. Raises IOError on disconnect."""
        try: received = self._recv(1024)
        except: received = ''

        while select.select([self._sock],[],[],0)[0]:
            try: add = self._recv(1024)
            except: add=''
            received +=add
            if not add: break

        if len(received): # length of 0 means disconnect
            self.DEBUG(received,'got')
        else:
            self.DEBUG('Socket error while receiving data','error')
            self.set_socket_state(SOCKET_DEAD)
            raise IOError("Peer disconnected")
        return received

    def send(self,stanza):
        self._owner.enqueue(self,stanza)

    def dispatch(self,stanza):
        if self._stream_state==STREAM_OPENED:                  # if the server really should reject all stanzas after he is closed stream (himeself)?
            return self.Dispatcher.dispatch(stanza,self)

    def fileno(self): return self._sock.fileno()

    def _stream_open(self,ns=None,tag='stream',attrs={}):
        text='<?xml version="1.0" encoding="utf-8"?>\n<stream:stream'
        if self.TYP=='client':
            text+=' to="%s"'%self.peer
        elif attrs.has_key('to'):
            text+=' from="%s" id="%s"'%(attrs['to'],self.ID)
        if attrs.has_key('xml:lang'): text+=' xml:lang="%s"'%attrs['xml:lang']
        if self.xmlns: xmlns=self.xmlns
        else: xmlns=NS_SERVER
        text+=' xmlns:xmpp="%s" xmlns:stream="%s" xmlns="%s" version="1.0"'%(NS_STANZAS,NS_STREAMS,xmlns)
        self.send(text+'>')
        self.set_stream_state(STREAM_OPENED)
        if self.TYP=='client': return
        if tag<>'stream': return self.terminate_stream(STREAM_INVALID_XML)
        if ns<>NS_STREAMS: return self.terminate_stream(STREAM_INVALID_NAMESPACE)
        if self.Stream.xmlns<>self.xmlns: return self.terminate_stream(STREAM_BAD_NAMESPACE_PREFIX)
        if not attrs.has_key('to'): return self.terminate_stream(STREAM_IMPROPER_ADDRESSING)
        if attrs['to'] not in self._owner.servernames: return self.terminate_stream(STREAM_HOST_UNKNOWN)
        self.servername=attrs['to'].lower()
        if self.TYP=='server': self.send_features()

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

    def feature(self,feature):
        if feature not in self.features: self.features.append(feature)
        self.unfeature(feature)

    def unfeature(self,feature):
        if feature in self.waiting_features: self.waiting_features.remove(feature)

    def _stream_close(self,unregister=1):
        if self._stream_state>=STREAM_CLOSED: return
        self.set_stream_state(STREAM_CLOSING)
        self.send('</stream:stream>')
        self.set_stream_state(STREAM_CLOSED)
        if unregister: self._owner.unregistersession(self)
        self._destroy_socket()

    def terminate_stream(self,error=None,unregister=1):
        if self._stream_state>=STREAM_CLOSING: return
        if self._stream_state<STREAM_OPENED:
            self.set_stream_state(STREAM_CLOSING)
            self._stream_open()
        else:
            p=Presence(typ='unavailable')
            p.setNamespace(NS_CLIENT)
            self.Dispatcher.dispatch(p,self)
        self.set_stream_state(STREAM_CLOSING)
        if error:
            if isinstance(error,Node): self.send(error)
            else: self.send(ErrorNode(error))
        self._stream_close(unregister=unregister)

    def _destroy_socket(self):
        """ breaking cyclic dependancy to let python's GC free memory just now """
        self.Stream.dispatch=None
        self.Stream.stream_footer_received=None
        self.Stream.stream_header_received=None
        self.Stream.destroy()
        self._sock.close()
        self.set_socket_state(SOCKET_DEAD)

    def set_socket_state(self,newstate):
        if type(newstate)==type(''): newstate=globals()[newstate]
        if self._socket_state<newstate: self._socket_state=newstate
    def set_auth_state(self,newstate):
        if type(newstate)==type(''): newstate=globals()[newstate]
        if self._auth_state<newstate: self._auth_state=newstate
    def set_stream_state(self,newstate):
        if type(newstate)==type(''): newstate=globals()[newstate]
        if self._stream_state<newstate: self._stream_state=newstate

class Server:
    def __init__(self,debug=['always']):
        self.sockets={}
        self.sockpoll=select.poll()

        self._DEBUG=Debug.Debug(debug)
        self.DEBUG=self._DEBUG.Show
        self.debug_flags=self._DEBUG.debug_flags
        self.debug_flags.append('session')
        self.debug_flags.append('dispatcher')
        self.debug_flags.append('server')

        self.SESS_LOCK=thread.allocate_lock()
        for port in [5222,5223,5269]:
            sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port+0))
            sock.listen(1)
            self.registersession(sock)

        self.Dispatcher=dispatcher.Dispatcher()
        self.Dispatcher._owner=self
        self.Dispatcher._init()

        self.features=[]
        for addon in modules.addons:
            if issubclass(addon,PlugIn): addon().PlugIn(self)
            else: self.__dict__[addon.__class__.__name__]=addon()
            self.feature(addon.NS)
        self.routes={}

    def feature(self,feature):
        if feature and feature not in self.features: self.features.append(feature)

    def enqueue(self,session,stanza):
        if session._stream_state>=STREAM_CLOSED or session._socket_state>=SOCKET_DEAD: return
        if type(stanza)==type(u''): stanza = stanza.encode('utf-8')
        elif type(stanza)<>type(''): stanza = stanza.__str__().encode('utf-8')
        """ TODO: Here not send actually but enqueue. """
        try:
            session._send(stanza)
            session.DEBUG(stanza,'sent')
        except:
            session.set_socket_state(SOCKET_DEAD)
            session.DEBUG("Socket error while sending data",'error')
            session.terminate_stream()

    def registersession(self,s):
        self.SESS_LOCK.acquire()
        self.sockets[s.fileno()]=s
        self.sockpoll.register(s,select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP)
        self.DEBUG('server','registered %s (%s)'%(s.fileno(),s))
        self.SESS_LOCK.release()

    def unregistersession(self,s):
        self.SESS_LOCK.acquire()
        if isinstance(s,Session):
            if s._socket_state>=SOCKET_UNREGISTERED:
                self.SESS_LOCK.release()
                if self._DEBUG.active: raise "Twice session unregistration!"
                else: return
            s.set_socket_state(SOCKET_UNREGISTERED)
        self.sockpoll.unregister(s)
        del self.sockets[s.fileno()]
        self.DEBUG('server','UNregistered %s (%s)'%(s.fileno(),s))
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
        if self.routes.has_key(peer): del self.routes[peer]
        return s

    def handle(self):
        for fileno,ev in self.sockpoll.poll():
            sock=self.sockets[fileno]
            if isinstance(sock,Session):
                sess=sock
                try: data=sess.receive()
                except IOError: # client closed the connection
                    sess.terminate_stream()
                    data=''
                if data:
                    try:
                        sess.Parse(data)
                    except simplexml.xml.parsers.expat.ExpatError:
                        sess.terminate_stream(STREAM_XML_NOT_WELL_FORMED)
                        del sess,sock
            elif isinstance(sock,socket.socket):
#            elif sock.typ in [CLIENT, SSLCLIENT, SERVER]:
                conn, addr = sock.accept()
                sess=Session(conn,self)      # behaive as server - announce features, etc.
                self.registersession(sess)
            else: raise "Unknown socket type: %s"%sock.typ

    def run(self):
        try:
            while 1: self.handle()
        except KeyboardInterrupt:
            self.DEBUG('server','Shutting down on user\'s behalf','info')
            self.shutdown()
#        except: self.shutdown(); raise

    def shutdown(self):
        socklist=self.sockets.keys()
        for fileno in socklist:
            s=self.sockets[fileno]
            if isinstance(s,socket.socket):
                self.unregistersession(s)
                s.shutdown(2)
                s.close()
            elif isinstance(s,Session): s.terminate_stream(STREAM_SYSTEM_SHUTDOWN)

    def Privacy(self,peer,stanza): pass

def test(server):
    conn=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect(('127.0.0.1',5222))
    sess=Session(conn,server,'localhost')
    server.registersession(sess)

s=Server()
if __name__=='__main__':
    print "Firing up PsyCo"
    import psyco
    psyco.log()
    psyco.full()
    s.run()
