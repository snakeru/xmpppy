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

# $Id$

from xmpp import *
import socket,select,random,os,modules

"""
_socket_state live/dead
_auth_state   no/in-process/yes
_stream_state not-opened/opened/closing/closed
"""
SOCKET_ALIVE        =1
SOCKET_DEAD         =2
SOCKET_UNREGISTERED =3
NOT_AUTHED =1
AUTHING    =2
AUTHED     =3
STREAM_NOT_OPENED =1
STREAM_OPENED     =2
STREAM_CLOSING    =3
STREAM_CLOSED     =4

class Session:
    def __init__(self,socket,server):
        self._sock=socket
        self._send=socket.send
        self._recv=socket.recv
        self.dispatcher=server.dispatcher
        self.DBG_LINE='session'
        self.DEBUG=server.dispatcher.DEBUG
        self._expected={}
        self._owner=server
        self.ID=`random.random()`[2:]
        self.StartStream()
        self._socket_state=SOCKET_ALIVE
        self._auth_state=NOT_AUTHED
        self.features=[]

    def StartStream(self):
        self._stream_state=STREAM_NOT_OPENED
        self.Stream=simplexml.NodeBuilder()
        self.Stream._dispatch_depth=2
        self.Stream.dispatch=self.dispatch
        self.Parse=self.Stream.Parse
        self.Stream.stream_header_received=self._stream_open
        self.Stream.stream_footer_received=self._stream_close

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
            return self.dispatcher.dispatch(stanza,self)

    def fileno(self): return self._sock.fileno()

    def _stream_open(self,ns=None,tag='stream',attrs={}):
        text='<?xml version="1.0" encoding="utf-8"?>\n<stream:stream'
        if attrs.has_key('to'): text+=' from="%s"'%attrs['to']
        if attrs.has_key('xml:lang'): text+=' xml:lang="%s"'%attrs['xml:lang']
        if self.Stream.xmlns in self.xmlns: xmlns=self.Stream.xmlns
        else: xmlns=self.xmlns[0]
        text+=' xmlns:xmpp="%s" xmlns:stream="%s" xmlns="%s" id="%s" version="1.0"'%(NS_STANZAS,NS_STREAMS,xmlns,self.ID)
        self.Stream.nsvoc={NS_STREAMS:'stream',NS_STANZAS:'xmpp'}
        self.send(text+'>')
        self.set_stream_state(STREAM_OPENED)
        if tag<>'stream': return self.terminate_stream(ERR_INVALID_XML)
        if ns<>NS_STREAMS: return self.terminate_stream(ERR_INVALID_NAMESPACE)
        if self.Stream.xmlns not in self.xmlns: return self.terminate_stream(ERR_BAD_NAMESPACE_PREFIX)
        if not attrs.has_key('to'): return self.terminate_stream(ERR_IMPROPER_ADDRESSING)
#        if attrs['to'] not in our_hosts: return self.terminate_stream(ERR_HOST_UNKNOWN)
        self.send_features()

    def send_features(self):
        features=Node('stream:features')
        if 'tls' not in self.features and self._owner.__dict__.has_key('sslcertfile') and self._owner.__dict__.has_key('TLS'):
            features.T.starttls.setNamespace(NS_TLS)
            features.T.starttls.T.required
        if 'sasl' not in self.features and self._owner.__dict__.has_key('SASL'):
            features.T.mechanisms.setNamespace(NS_SASL)
            features.T.mechanisms.T.mechanism='DIGEST-MD5'
            features.T.mechanisms.NT.mechanism='PLAIN'
        self.send(features)

    def _stream_close(self):
        if self._stream_state>=STREAM_CLOSED: return
        self.send('</stream:stream>')
        self.set_stream_state(STREAM_CLOSED)
        self._owner.unregistersession(self)

    def terminate_stream(self,error=None):
        if self._stream_state>=STREAM_CLOSING: return
        if self._stream_state<STREAM_OPENED:
            self.set_stream_state(STREAM_CLOSING)
            self._stream_open()
        self.set_stream_state(STREAM_CLOSING)
        if error: self.send(ErrorNode(error))
        self._stream_close()

    def _destroy_socket(self):
        """ workaround for bug in xml.parsers.expat. See http://bugs.debian.org/271619 """
        try:
            self._sock.shutdown(2)
            self._sock.close()
        except: pass
        self.set_socket_state(SOCKET_DEAD)

    def set_socket_state(self,newstate):
        if self._socket_state<newstate: self._socket_state=newstate
    def set_auth_state(self,newstate):
        if self._auth_state<newstate: self._auth_state=newstate
    def set_stream_state(self,newstate):
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

        for port in [5222,5223,5269]:
            sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port+0))
            sock.listen(1)
            self.registersession(sock)

        self.dispatcher=dispatcher.Dispatcher()
        self.dispatcher._owner=self
        self.dispatcher._init()

        for addon in modules.addons: addon().PlugIn(self)

    def enqueue(self,session,stanza):
        if session._stream_state>=STREAM_CLOSED or session._socket_state>=SOCKET_DEAD: return
        if type(stanza)==type(u''): stanza = stanza.encode('utf-8')
        elif type(stanza)<>type(''): stanza = stanza.__str__(nsvoc=session.Stream.nsvoc).encode('utf-8')
        """ TODO: Here not send actually but enqueue. """
        try:
            session._send(stanza)
            session.DEBUG(stanza,'sent')
        except:
            session.DEBUG("Socket error while sending data",'error')
            session.terminate_stream()

    def registersession(self,s):
        self.sockets[s.fileno()]=s
        self.sockpoll.register(s,select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP)
        self.DEBUG('server','registered %s (%s)'%(s.fileno(),s))

    def unregistersession(self,s):
        if isinstance(s,Session):
            if s._socket_state>=SOCKET_UNREGISTERED:
                if self._DEBUG.active: raise "Twice session unregistration!"
                else: return
            s.set_socket_state(SOCKET_UNREGISTERED)
        self.sockpoll.unregister(s)
        del self.sockets[s.fileno()]
        if isinstance(s,Session): s._destroy_socket() # destructor. Bug workaround.
        else: s.shutdown(2); s.close()

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
                        sess.terminate_stream(ERR_XML_NOT_WELL_FORMED)
                        del sess,sock
            elif isinstance(sock,socket.socket):
#            elif sock.typ in [CLIENT, SSLCLIENT, SERVER]:
                conn, addr = sock.accept()
                sess=Session(conn,self)
                host,port=sock.getsockname()
                if port in [5222,5223]: sess.xmlns=[NS_CLIENT,NS_SERVER]
                else: sess.xmlns=[NS_SERVER]
                self.registersession(sess)
            else: raise "Unknown socket type: %s"%sock.typ

    def run(self):
        import psyco
        psyco.log()
        psyco.full()
        try:
            while 1:
              self.handle()
        except:
            self.shutdown()
            raise

    def shutdown(self):
        socklist=self.sockets.keys()
        for fileno in socklist:
            s=self.sockets[fileno]
            if isinstance(s,socket.socket): self.unregistersession(s)
            elif isinstance(s,Session): s.terminate_stream(ERR_SYSTEM_SHUTDOWN)

Server().run()
