#!/usr/bin/python
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# roster implemetation for xmppd.py
# made for mblsha

# $Id: roster.py,v 1.1 2004-10-25 11:55:29 snakeru Exp $

from xmpp import *
from db_fake import db

class Roster(PlugIn):
    NS=NS_ROSTER
    def plugin(self,server):
        server.Dispatcher.RegisterHandler('iq',self.getRosterHandler,'get',NS_ROSTER)
        server.Dispatcher.RegisterHandler('iq',self.setRosterHandler,'set',NS_ROSTER)

    def getRosterHandler(self,sess,stanza):
        iq=stanza
        iq.setType('result')
        q=iq.T.query
        for server in db.keys():
            for user in db[server].keys():
                item=q.NT.item
                item.setAttr('jid','%s@%s'%(user,server))
                item.setAttr('subscription','both')
                item.setAttr('name',user)
        sess.send(iq)
        raise NodeProcessed

    def setRosterHandler(self,sess,stanza):
        sess.send(Error(stanza,ERR_FEATURE_NOT_IMPLEMENTED))
        raise NodeProcessed

class vCard(PlugIn):
    NS=NS_VCARD
    def plugin(self,server):
        server.Dispatcher.RegisterHandler('iq',self.dummyHandler,'get',NS_VCARD)
        server.Dispatcher.RegisterHandler('iq',self.dummyHandler,'set',NS_VCARD)

    def dummyHandler(self,sess,stanza):
        iq=stanza.buildReply('result')
        sess.send(iq)
        raise NodeProcessed
