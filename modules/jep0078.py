# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# JEP0078 (Non-SASL authenticaion) for xmppd.py

# $Id: jep0078.py,v 1.4 2004-10-08 19:12:06 snakeru Exp $

from xmpp import *
import sha

class NSA(PlugIn):
    NS=NS_AUTH
    def plugin(self,server):
        server.Dispatcher.RegisterHandler('iq',self.getAuthInfoHandler,'get',NS_AUTH)
        server.Dispatcher.RegisterHandler('iq',self.setAuthInfoHandler,'set',NS_AUTH)

    def getAuthInfoHandler(self,session,stanza):
        servername=stanza['to']
        if servername and servername not in self._owner.servernames:
            session.send(Error(stanza,ERR_ITEM_NOT_FOUND))
        else:
            iq=stanza.buildReply('result')
            iq.T.query.T.username=stanza.T.query.T.username
            iq.T.query.T.password
            iq.T.query.T.digest
            iq.T.query.T.resource
            session.send(iq)
        raise NodeProcessed

    def setAuthInfoHandler(self,session,stanza):
        servername=stanza['to'].getDomain().lower()
        username=stanza.T.query.T.username.getData().lower()
        password=self._owner.AUTH.getpassword(username,servername)
        if password is not None: digest=sha.new(session.ID+password).hexdigest()
        if servername not in self._owner.servernames:
            iq=Error(stanza,ERR_ITEM_NOT_FOUND)
        elif session.ourname==servername \
          and password \
          and (stanza.T.query.T.password.getData()==password \
           or stanza.T.query.T.digest.getData()==digest ) \
          and stanza.T.query.T.resource.getData():
            iq=stanza.buildReply('result')
            fulljid="%s@%s/%s"%(username,servername,stanza.T.query.T.resource.getData())
            session.peer=fulljid
            s=self._owner.deactivatesession(fulljid)
            if s: s.terminate_stream(STREAM_CONFLICT)
            session.set_auth_state('SESSION_OPENED')
        else:
            iq=stanza.buildReply('error')
        session.send(iq)
        raise NodeProcessed
