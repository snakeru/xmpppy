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

# $Id: xmppd.py,v 1.1 2004-09-15 02:41:06 snakeru Exp $

from xmpp import *
import socket,select

SOCKET_LISTEN_CLIENT=1
SOCKET_LISTEN_SSLCLIENT=2
SOCKET_LISTEN_SERVER=3
SESSION=4

class XMPPSocket(socket.socket): pass

class Session:
    def __init__(self,socket,server):
        self._sock=socket
        self.typ=SESSION
        self._send=socket.send
        self._recv=socket.recv
        self.dispatcher=server.dispatcher
        self.DBG_LINE='session'
        self.DEBUG=server.dispatcher.DEBUG
        self._expected={}
        self._owner=server
        self.StartStream()

    def StartStream(self):
        self.Stream=simplexml.NodeBuilder()
        self.Stream._dispatch_depth=2
        self.Stream.dispatch=self.dispatch
        self.Parse=self.Stream.Parse
        self.Stream.stream_header_received=self.stream_open
        self.Stream.stream_footer_received=self.stream_close

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
            raise IOError("Peer disconnected")
        return received

    def send(self,stanza):
        self._owner.enqueue(self,stanza)

    def dispatch(self,stanza): return self.dispatcher.dispatch(stanza,self)
    def fileno(self): return self._sock.fileno()
    def stream_open(self): self.send('<stream:stream>'); print "START??!"
    def stream_close(self): self.send('</stream:stream>'); print "Stop..."

class Server:
    def __init__(self,debug=['always']):
        self.sockets={}
        self.sockpoll=select.poll()

        sock=XMPPSocket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 5222))
        sock.listen(1)
        sock.typ=SOCKET_LISTEN_CLIENT
        self.registersession(sock)

        self._DEBUG=Debug.Debug(debug)
        self.DEBUG=self._DEBUG.Show
        self.debug_flags=self._DEBUG.debug_flags
        self.debug_flags.append('session')
        self.debug_flags.append('dispatcher')
        self.dispatcher=dispatcher.Dispatcher()
        self.dispatcher._owner=self
        self.dispatcher._init()

    def enqueue(self,session,stanza):
        if type(stanza)==type(u''): stanza = stanza.encode('utf-8')
        elif type(stanza)<>type(''): stanza = ustr(stanza).encode('utf-8')
        """ TODO: Here not send actually but enqueue. """
        try:
            session._send(stanza)
            session.DEBUG(stanza,'sent')
        except:
            session.DEBUG("Socket error while sending data",'error')
            self.unregistersession(session)

    def registersession(self,s):
        self.sockets[s.fileno()]=s
        self.sockpoll.register(s,select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP)

    def unregistersession(self,s):
        self.sockpoll.unregister(s)
        del self.sockets[s.fileno()]
        s._sock.shutdown(2) ; s._sock.close() # workaround for bug in xml.parsers.expat. See http://bugs.debian.org/271619

    def handle(self):
        for fileno,ev in self.sockpoll.poll():
            sock=self.sockets[fileno]
            if isinstance(sock,Session):
                sess=sock
                try: data=sess.receive()
                except IOError: # client closed the connection
                    self.unregistersession(sess)
                    data=''
                if data:
                    try:
                        sess.Parse(data)
                    except simplexml.xml.parsers.expat.ExpatError:
                        sess.send("Invalid XML\n")
                        self.unregistersession(sess)
                        del sess,sock
            elif isinstance(sock,socket.socket):
#            elif sock.typ in [SOCKET_LISTEN_CLIENT,SOCKET_LISTEN_SSLCLIENT,SOCKET_LISTEN_SERVER]:
                conn, addr = sock.accept()
                sess=Session(conn,self)
                self.registersession(sess)
            else: raise "Unknown socket type: %s"%sock.typ

s=Server()
for i in range(30):
  s.handle()


