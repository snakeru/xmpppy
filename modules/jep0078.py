#!/usr/bin/python
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# JEP0078 (Non-SASL authenticaion) for xmppd.py

# $Id: jep0078.py,v 1.2 2004-09-19 20:20:05 snakeru Exp $

from xmpp import *

class NSA(PlugIn):
    def plugin(self,server):
        server.Dispatcher.RegisterHandler('iq',self.getAuthInfoHandler,'get',NS_AUTH)
        server.Dispatcher.RegisterHandler('iq',self.setAuthInfoHandler,'set',NS_AUTH)

    def getAuthInfoHandler(self,sess,stanza):
        name=stanza['to']
        if name not in self._owner.servernames:
            sess.send(Error(stanza,ERR_ITEM_NOT_FOUND))
        else:
            iq=stanza.buildReply('result')
            iq.T.query.T.username=stanza.T.query.T.username
            iq.T.query.T.password
            iq.T.query.T.digest
            iq.T.query.T.resource
            sess.send(iq)
        raise NodeProcessed

    def setAuthInfoHandler(self,sess,stanza):
        sess.send(Error(stanza,ERR_NOT_AUTHORIZED))     # dummy code for now
        raise NodeProcessed
