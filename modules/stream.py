#!/usr/bin/python
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# Stream-level features for xmppd.py

# $Id: stream.py,v 1.1 2004-09-17 19:53:01 snakeru Exp $

from xmpp import *
import socket
from tlslite.api import *

class TLS(PlugIn):
    def plugin(self,server):
        server.dispatcher.RegisterHandlerOnce('starttls',self.starttlsHandler,xmlns=NS_TLS)

    def starttlsHandler(self,session,stanza):
        if self._owner.__dict__.has_key('sslcertfile'): certfile=self._owner.sslcertfile
        else: certfile=None
        if self._owner.__dict__.has_key('sslkeyfile'): keyfile=self._owner.sslkeyfile
        else: keyfile=certfile
        try: open(certfile) ; open(keyfile)
        except: certfile=None
        if not certfile or not keyfile:
            session.send(Node('failure',{'xmlns':NS_TLS}))
            raise NodeProcessed
        session.send(Node('proceed',{'xmlns':NS_TLS}))

        x509 = X509()
        x509.parse(open(certfile).read())
        certChain = X509CertChain([x509])
        privateKey = parsePEMKey(open(keyfile).read(), private=True)
        connection = TLSConnection(session._sock)
        connection.handshakeServer(certChain=certChain, privateKey=privateKey, reqCert=False)

        session.sslobj=connection
        session._recv=connection.read
        session._send=connection.write

        session.features.append('tls')
        session.StartStream()

class SASL(PlugIn): pass
