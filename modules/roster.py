#!/usr/bin/python
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# static roster implemetation for xmppd.py

# $Id: roster.py,v 1.2 2004-10-27 18:42:25 snakeru Exp $

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
        to,frm=[],[]
        for server in db.keys():
            for user in db[server].keys():
                item=q.NT.item
                jid,sub,name='%s@%s'%(user,server),'both',user
                item.setAttr('jid',jid)
                item.setAttr('subscription',sub)
                item.setAttr('name',name)
                if sub in ['to','both']: to.append(jid)
                if sub in ['from','both']: frm.append(jid)
        sess.enqueue(iq)
        raise NodeProcessed

    def setRosterHandler(self,sess,stanza):
        sess.enqueue(Error(stanza,ERR_FEATURE_NOT_IMPLEMENTED))
        raise NodeProcessed

    def getSubTo(self,session):
        list=[]
        for server in db.keys():
            for user in db[server].keys():
                jid=user+'@'+server
                list.append(jid)
        return list
    getSubFrom=getSubTo

class vCard(PlugIn):
    NS=NS_VCARD
    def plugin(self,server):
        server.Dispatcher.RegisterHandler('iq',self.dummyHandler,'get',NS_VCARD)
        server.Dispatcher.RegisterHandler('iq',self.dummyHandler,'set',NS_VCARD)

    def dummyHandler(self,sess,stanza):
        iq=stanza.buildReply('result')
        sess.enqueue(iq)
        raise NodeProcessed
