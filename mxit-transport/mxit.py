#! /usr/bin/env python
# $Id$
version = 'CVS ' + '$Revision$'.split()[1]
#
# MXit Transport
# 2006 Copyright (c) Norman Rasmussen
#
# This program is free software licensed with the GNU Public License Version 2.
# For a full copy of the license please go here http://www.gnu.org/licenses/licenses.html#GPL

import base64, ConfigParser, os, platform, re, select, sha, shelve, signal, socket, sys, time, traceback
import xmpp.client
from xmpp.protocol import *
from xmpp.browser import *
from xmpp.jep0106 import *
import config, xmlconfig, mxitlib
from adhoc import AdHocCommands
#from toolbox import *

VERSTR = 'MXit Transport'
rdsocketlist = {}
wrsocketlist = {}
#each item is a tuple of 4 values, 0 == frequency in seconds, 1 == offset from 0, 2 == function, 3 == arguments
timerlist = []

NODE_AVATAR='jabber:x:avatar x'
NODE_VCARDUPDATE='vcard-temp:x:update x'
NODE_ADMIN='admin'
NODE_ADMIN_REGISTERED_USERS='registered-users'
NODE_ADMIN_ONLINE_USERS='online-users'
NODE_ROSTER='roster'

def MXitIDEncode(mxitid):
    return mxitid.replace('@','%')

def MXitIDDecode(mxitid):
    return '@'.join(mxitid.rsplit('%',1))

roomenccodere = re.compile('([^-]?)([A-Z-])')
def RoomEncode(mxitid):
    return JIDEncode(roomenccodere.sub('\\1-\\2', mxitid))

roomdeccodere = re.compile('-([a-zA-Z-])')
def RoomDecode(mxitid):
    def decode(m):
        return m.group(1).upper()
    return roomdeccodere.sub(decode, JIDDecode(mxitid))

class Transport:

    # This class is the main collection of where all the handlers for both the MXit and Jabber

    #Global structures
    userlist = {}
    discoresults = {}
    online = 1
    restart = 0
    offlinemsg = ''

    def __init__(self,jabber):
        self.jabber = jabber
        self.chatcat = {0:(0,{})}
        self.catlist = {}

    def jabberqueue(self,packet):
        if not wrsocketlist.has_key(self.jabber.Connection._sock):
            wrsocketlist[self.jabber.Connection._sock]=[]
        wrsocketlist[self.jabber.Connection._sock].append(packet)

    def mxitqueue(self,fromjid,packet):
        if packet != None:
            s = self.userlist[fromjid].sock
            if not wrsocketlist.has_key(s):
                wrsocketlist[s]=[]
            wrsocketlist[s].append(packet)

    def findbadconn(self):
        #print rdsocketlist
        for each in self.userlist:
            if config.dumpProtocol: print each, self.userlist[each].sock.fileno()
            if self.userlist[each].sock.fileno() == -1:
                #print each, self.userlist[each].sock.fileno()
                self.mxit_closed(self.userlist[each])
            else:
                try:
                    a,b,c = select.select([self.userlist[each].sock],[self.userlist[each].sock],[self.userlist[each].sock],0)
                except:
                    self.mxit_closed(self.userlist[each])
        badlist = []
        for each in wrsocketlist.keys():
            try:
                if each.fileno() == -1:
                    badlist.append(each)
            except:
                    badlist.append(each)
        for each in badlist:
            del wrsocketlist[each]
        return

    def register_handlers(self):
        self.jabber.RegisterHandler('message',self.xmpp_message)
        self.jabber.RegisterHandler('presence',self.xmpp_presence)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_discoinfo_results,typ = 'result', ns=NS_DISCO_INFO)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_version,typ = 'get', ns=NS_VERSION)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_register_get, typ = 'get', ns=NS_REGISTER)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_register_set, typ = 'set', ns=NS_REGISTER)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_gateway_get, typ = 'get', ns=NS_GATEWAY)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_gateway_set, typ = 'set', ns=NS_GATEWAY)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_vcard, typ = 'get', ns=NS_VCARD)
        self.disco = Browser()
        self.disco.PlugIn(self.jabber)
        self.adhoccommands = AdHocCommands(userfile)
        self.adhoccommands.PlugIn(self)
        self.disco.setDiscoHandler(self.xmpp_base_disco,node='',jid=config.jid)
        self.disco.setDiscoHandler(self.xmpp_base_disco,node='',jid='')

    def register_mxit_handlers(self, con):
        con.handlers['online']= self.mxit_online
        con.handlers['offline']= self.mxit_offline
        con.handlers['login'] = self.mxit_login
        con.handlers['loginfail'] = self.mxit_loginfail
        con.handlers['subscribe'] = self.mxit_subscribe
        con.handlers['message'] = self.mxit_message
        con.handlers['messagefail'] = self.mxit_messagefail
        con.handlers['closed'] = self.mxit_closed

    def xmpp_message(self, con, event):
        fromjid = event.getFrom()
        if fromjid == None:
            return
        fromstripped = fromjid.getStripped().encode('utf8')
        if event.getTo().getNode() != None:
            if self.userlist.has_key(fromstripped):
                if event.getTo().getDomain() == config.jid:
                    mxitid = MXitIDDecode(event.getTo().getNode())
                    mxitidenc = mxitid.encode('utf-8')
                    if event.getBody() == None:
                        return
                    # normal non-groupchat or conference cases
                    if event.getType() == None or event.getType() =='normal':
                        # normal message case
                        #print 'got message'
                        self.mxitqueue(fromstripped,self.userlist[fromstripped].mxit_send_message(mxitidenc,event.getBody().encode('utf-8')))
                    elif event.getType() == 'chat':
                        # normal chat case
                        #print 'got message'
                        self.mxitqueue(fromstripped,self.userlist[fromstripped].mxit_send_message(mxitidenc,event.getBody().encode('utf-8')))
                    else:
                        #print 'type error'
                        self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                else:
                    self.jabberqueue(Error(event,ERR_BAD_REQUEST))
            else:
                if config.dumpProtocol: print 'no item error'
                self.jabberqueue(Error(event,ERR_REGISTRATION_REQUIRED))
        else:
            self.jabberqueue(Error(event,ERR_BAD_REQUEST))

    def xmpp_presence(self, con, event):
        mxitobj = None
        mxitrost = None
        fromjid = event.getFrom()
        fromstripped = fromjid.getStripped().encode('utf8')
        if userfile.has_key(fromstripped):
            if event.getTo().getDomain() == config.jid:
                mxitid = MXitIDDecode(event.getTo().getNode())
                mxitidenc = mxitid.encode('utf-8')
                if event.getType() == 'subscribed':
                    if self.userlist.has_key(fromstripped):
                        if event.getTo() == config.jid:
                            conf = userfile[fromstripped]
                            conf['subscribed']=True
                            userfile[fromstripped]=conf
                            userfile.sync()
                            #For each new user check if rosterx is adversited then do the rosterx message, else send a truckload of subscribes.
                            #Part 1, parse the features out of the disco result
                            features = []
                            if self.discoresults.has_key(event.getFrom().getStripped().encode('utf8')):
                                discoresult = self.discoresults[event.getFrom().getStripped().encode('utf8')]
                                #for i in discoresult.getQueryPayload():
                                if discoresult.getTag('query').getTag('feature'): features.append(discoresult.getTag('query').getAttr('var'))
                            #Part 2, make the rosterX message
                            if NS_ROSTERX in features:
                                m = Message(to = fromjid, frm = config.jid, subject= 'MXit Roster Items', body = 'Items from MXit Roster')
                                p=None
                                p= m.setTag('x',namespace = NS_ROSTERX)
                                mxitrost = self.userlist[fromstripped].buddylist
                                if config.dumpProtocol: print mxitrost
                                for each in mxitrost.keys():
                                    for (mxitid,nick) in mxitrost[each]:
                                        p.addChild(name='item', attrs={'jid':'%s@%s'%(MXitIDEncode(mxitid),config.jid),'name':nick, 'action':'add'},payload=[Node('group',payload=each)])
                                self.jabberqueue(m)
                                if config.dumpProtocol: print m
                            else:
                                for each in self.userlist[fromstripped].buddylist.keys():
                                    for (mxitid,nick) in self.userlist[fromstripped].buddylist[each]:
                                        self.jabberqueue(Presence(frm='%s@%s'%(MXitIDEncode(mxitid),config.jid),to = fromjid, typ='subscribe', status='MXit messenger contact'))
                            m = Presence(to = fromjid, frm = config.jid)
                            self.jabberqueue(m)
                            self.mxit_send_online(fromstripped)
                            self.register_mxit_handlers(self.userlist[fromstripped])
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'subscribe':
                    if self.userlist.has_key(fromstripped):
                        if event.getTo() == config.jid:
                            conf = userfile[fromstripped]
                            conf['usubscribed']=True
                            userfile[fromstripped]=conf
                            userfile.sync()
                            m = Presence(to = fromjid, frm = config.jid, typ = 'subscribed')
                            self.jabberqueue(m)
                        elif self.userlist[fromstripped].roster.has_key(mxitidenc):
                            m = Presence(to = fromjid, frm = event.getTo(), typ = 'subscribed')
                            self.jabberqueue(m)
                        else:
                            #add new user case.
                            if event.getStatus() != None:
                                if config.dumpProtocol: print event.getStatus().encode('utf-8')
                                status = event.getStatus().encode('utf-8')
                            else:
                                status = ''
                            self.mxitqueue(fromstripped,self.userlist[fromstripped].mxit_send_addbuddy(mxitidenc, status))
                            self.jabberqueue(Presence(frm=event.getTo(), to = event.getFrom(), typ = 'subscribed'))
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'unsubscribe':
                    if self.userlist.has_key(fromstripped):
                        if self.userlist[fromstripped].roster.has_key(mxitid):
                            if event.getStatus() != None:
                                msg = event.getStatus().encode('utf-8')
                            else:
                                msg = ''
                            self.mxitqueue(fromstripped,self.userlist[fromstripped].mxit_send_delbuddy(mxitidenc, msg))
                            self.jabberqueue(Presence(frm=event.getTo(), to = event.getFrom(), typ = 'unsubscribed'))
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'unsubscribed':
                    # should do something more elegant here
                    pass
                elif event.getType() == None or event.getType() == 'available' or event.getType() == 'invisible':
                    # code to add mxit connection goes here
                    if mxitid != '':
                        return
                    if self.userlist.has_key(fromstripped):
                        # update status case and additional resource case
                        # update status case
                        if self.userlist[fromstripped].xresources.has_key(event.getFrom().getResource()):
                            #update resource record
                            self.userlist[fromstripped].xresources[event.getFrom().getResource()]=(event.getShow(),event.getPriority(),event.getStatus(),self.userlist[fromstripped].xresources[event.getFrom().getResource()][3])
                            if config.dumpProtocol: print "Update resource login: %s" % self.userlist[fromstripped].xresources
                        else:
                            #new resource login
                            self.userlist[fromstripped].xresources[event.getFrom().getResource()]=(event.getShow(),event.getPriority(),event.getStatus(),time.time())
                            if config.dumpProtocol: print "New resource login: %s" % self.userlist[fromstripped].xresources
                            #send roster as is
                            self.mxit_send_online(fromstripped,event.getFrom().getResource())
                        #print fromstripped, event.getShow().encode('utf-8'), event.getStatus().encode('utf-8')
                        self.xmpp_presence_do_update(event,fromstripped)
                    else:
                        # open connection case
                        try:
                            conf = userfile[fromstripped]
                        except:
                            self.jabberqueue(Message(to=fromstripped,subject='Transport Configuration Error',body='The transport has found that your configuration could not be loaded. Please re-register with the transport'))
                            del userfile[fromstripped]
                            userfile.sync()
                            return
                        mxitobj = mxitlib.MXitCon(conf['username'].encode('utf-8'),conf['password'].encode('utf-8'),conf['clientid'].encode('utf-8'), fromstripped,config.host,config.dumpProtocol)
                        #self.userlist[fromstripped]=mxitobj
                        s = mxitobj.connect()
                        if s != None:
                            rdsocketlist[s]=mxitobj
                            self.userlist[mxitobj.fromjid]=mxitobj
                            self.register_mxit_handlers(self.userlist[fromstripped])
                            self.mxitqueue(fromstripped,mxitobj.mxit_send_login())
                            mxitobj.event = event
                            if event.getShow() == 'xa' or event.getShow() == 'away':
                                mxitobj.away = 'away'
                            elif event.getShow() == 'dnd':
                                mxitobj.away = 'dnd'
                            elif event.getShow() == 'invisible':
                                mxitobj.away = 'invisible'
                            else:
                                mxitobj.away = None
                            mxitobj.showstatus = event.getStatus()
                            #Add line into currently matched resources
                            mxitobj.xresources[event.getFrom().getResource()]=(event.getShow(),event.getPriority(),event.getStatus(),time.time())
                        else:
                            self.jabberqueue(Error(event,ERR_REMOTE_SERVER_TIMEOUT))
                elif event.getType() == 'unavailable':
                    # Match resources and remove the newly unavailable one
                    if self.userlist.has_key(fromstripped):
                        #print 'Resource: ', event.getFrom().getResource(), "To Node: ",mxitid
                        if mxitid =='':
                            #self.mxit_send_offline(fromstripped,event.getFrom().getResource())
                            if self.userlist[fromstripped].xresources.has_key(event.getFrom().getResource()):
                                del self.userlist[fromstripped].xresources[event.getFrom().getResource()]
                                self.xmpp_presence_do_update(event,fromstripped)
                            #Single resource case
                            #print self.userlist[fromstripped].xresources
                            if self.userlist[fromstripped].xresources == {}:
                                if config.dumpProtocol: print 'No more resource logins'
                                self.mxitqueue(fromstripped,self.userlist[fromstripped].mxit_send_offline())
                                self.userlist[fromstripped].away = 'unavailable'
                            #    mxitobj=self.userlist[fromstripped]
                            #    del self.userlist[mxitobj.fromjid]
                            #    if rdsocketlist.has_key(mxitobj.sock):
                            #        del rdsocketlist[mxitobj.sock]
                            #    if wrsocketlist.has_key(mxitobj.sock):
                            #        del wrsocketlist[mxitobj.sock]
                            #    mxitobj.sock.close()
                            #    del mxitobj
                    else:
                        self.jabberqueue(Presence(to=fromjid,frm = config.jid, typ='unavailable'))
            else:
                self.jabberqueue(Error(event,ERR_BAD_REQUEST))
        else:
            # Need to add auto-unsubscribe on probe events here.
            if event.getType() == 'probe':
                self.jabberqueue(Presence(to=event.getFrom(), frm=event.getTo(), typ='unsubscribe'))
                self.jabberqueue(Presence(to=event.getFrom(), frm=event.getTo(), typ='unsubscribed'))
            elif event.getType() == 'unsubscribed':
                pass
            elif event.getType() == 'unsubscribe':
                self.jabberqueue(Presence(frm=event.getTo(),to=event.getFrom(),typ='unsubscribed'))
            else:
                self.jabberqueue(Error(event,ERR_REGISTRATION_REQUIRED))

    def xmpp_presence_do_update(self,event,fromstripped):
        age =None
        priority = None
        resource = None
        for each in self.userlist[fromstripped].xresources.keys():
            #print each,self.userlist[fromstripped].xresources
            if self.userlist[fromstripped].xresources[each][1]>priority:
                #if priority is higher then take the highest
                age = self.userlist[fromstripped].xresources[each][3]
                priority = self.userlist[fromstripped].xresources[each][1]
                resource = each
            elif self.userlist[fromstripped].xresources[each][1]==priority:
                #if priority is the same then take the oldest
                if self.userlist[fromstripped].xresources[each][3]<age:
                    age = self.userlist[fromstripped].xresources[each][3]
                    priority = self.userlist[fromstripped].xresources[each][1]
                    resource = each
        if resource == event.getFrom().getResource():
            #only update shown status if resource is current datasource
            self.mxitqueue(fromstripped,self.userlist[fromstripped].mxit_send_online(event.getShow(),event.getStatus()))
            self.userlist[fromstripped].away = event.getShow()

    # New Disco Handlers
    def xmpp_base_disco(self, con, event, type):
        fromjid = event.getFrom().getStripped().__str__()
        fromstripped = event.getFrom().getStripped().encode('utf8')
        to = event.getTo()
        node = event.getQuerynode();
        if to == config.jid:
            if node == None:
                if type == 'info':
                    features = [NS_VERSION,NS_COMMANDS,NS_AVATAR]
                    if config.allowRegister or userfile.has_key(fromjid):
                        features = [NS_REGISTER] + features
                    return {
                        'ids':[
                            {'category':'gateway','type':'mxit','name':VERSTR}],
                        'features':features}
                if type == 'items':
                    list = [
                        {'node':NODE_ROSTER,'name':config.discoName + ' Roster','jid':config.jid}]
                    if fromjid in config.admins:
                        list.append({'node':NODE_ADMIN,'name':config.discoName + ' Admin','jid':config.jid})
                    return list
            elif node == NODE_ADMIN:
                if type == 'info':
                    return {'ids':[],'features':[]}
                if type == 'items':
                    if not fromjid in config.admins:
                        return []
                    return [
                        {'node':NS_COMMANDS,'name':config.discoName + ' Commands','jid':config.jid},
                        {'node':NODE_ADMIN_REGISTERED_USERS,'name':config.discoName + ' Registered Users','jid':config.jid},
                        {'node':NODE_ADMIN_ONLINE_USERS,'name':config.discoName + ' Online Users','jid':config.jid}]
            elif node == NODE_ROSTER:
                if type == 'info':
                    return {'ids':[],'features':[]}
                if type == 'items':
                    list = []
                    if self.userlist.has_key(fromstripped):
                        for mxitid in self.userlist[fromstripped].roster.keys():
                            list.append({'jid':'%s@%s' %(MXitIDEncode(mxitid),config.jid),'name':mxitid})
                    return list
            elif node.startswith(NODE_ADMIN_REGISTERED_USERS):
                if type == 'info':
                    return {'ids':[],'features':[]}
                if type == 'items':
                    if not fromjid in config.admins:
                        return []
                    nodeinfo = node.split('/')
                    list = []
                    if len(nodeinfo) == 1:
                        for each in userfile.keys():
                            #list.append({'node':'/'.join([NODE_ADMIN_REGISTERED_USERS, each]),'name':each,'jid':config.jid})
                            list.append({'name':each,'jid':each})
                    #elif len(nodeinfo) == 2:
                        #fromjid = nodeinfo[1]
                        #list = [
                            #{'name':fromjid + ' JID','jid':fromjid}]
                    return list
            elif node.startswith(NODE_ADMIN_ONLINE_USERS):
                if type == 'info':
                    return {'ids':[],'features':[]}
                if type == 'items':
                    if not fromjid in config.admins:
                        return []
                    nodeinfo = node.split('/')
                    list = []
                    if len(nodeinfo) == 1:
                        for each in self.userlist.keys():
                            #list.append({'node':'/'.join([NODE_ADMIN_ONLINE_USERS, each]),'name':each,'jid':config.jid})
                            list.append({'name':each,'jid':each})
                    #elif len(nodeinfo) == 2:
                        #fromjid = nodeinfo[1]
                        #list = [
                            #{'name':fromjid + ' JID','jid':fromjid}]
                    return list
            else:
                self.jabber.send(Error(event,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
        elif to.getDomain() == config.jid:
            if self.userlist.has_key(fromstripped):
                mxitid = MXitIDDecode(event.getTo().getNode())
                if type == 'info':
                    if self.userlist[fromstripped].roster.has_key(mxitid):
                        features = [NS_VCARD,NS_VERSION]
                        if userfile[fromstripped.encode('utf-8')].has_key('avatar'):
                            if userfile[fromstripped.encode('utf-8')]['avatar'].has_key(mxitid):
                                features.append(NS_AVATAR)
                        return {
                            'ids':[
                                {'category':'client','type':'mxit','name':mxitid}],
                            'features':features}
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                if type == 'items':
                    if self.userlist[fromstripped].roster.has_key(mxitid):
                        return []
            else:
                self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))

    def xmpp_iq_discoinfo_results(self, con, event):
        self.discoresults[event.getFrom().getStripped().encode('utf8')]=event
        raise NodeProcessed

    def xmpp_iq_register_get(self, con, event):
        if event.getTo() == config.jid:
            username = []
            password = []
            clientid = []
            fromjid = event.getFrom().getStripped().encode('utf8')
            queryPayload = [Node('instructions', payload = 'Please provide your MXit username and password')]
            if userfile.has_key(fromjid):
                try:
                    username = userfile[fromjid]['username']
                    password = userfile[fromjid]['password']
                    clientid = userfile[fromjid]['clientid']
                except:
                    pass
                queryPayload += [
                    Node('username',payload=username),
                    Node('password',payload=password),
                    Node('misc',payload=clientid),
                    Node('registered')]
            else:
                if not config.allowRegister:
                    return
                queryPayload += [
                    Node('username'),
                    Node('password'),
                    Node('misc')]
            m = event.buildReply('result')
            m.setQueryNS(NS_REGISTER)
            m.setQueryPayload(queryPayload)
            self.jabberqueue(m)
            #Add disco#info check to client requesting for rosterx support
            i= Iq(to=event.getFrom(), frm=config.jid, typ='get',queryNS=NS_DISCO_INFO)
            self.jabberqueue(i)
        else:
            self.jabberqueue(Error(event,ERR_BAD_REQUEST))
        raise NodeProcessed

    def xmpp_iq_register_set(self, con, event):
        if event.getTo() == config.jid:
            remove = False
            username = False
            password = False
            clientid = False
            fromjid = event.getFrom().getStripped().encode('utf8')
            #for each in event.getQueryPayload():
            #    if each.getName() == 'username':
            #        username = each.getData()
            #        print "Have username ", username
            #    elif each.getName() == 'password':
            #        password = each.getData()
            #        print "Have password ", password
            #    elif each.getName() == 'remove':
            #        remove = True
            query = event.getTag('query')
            if query.getTag('username'):
                username = query.getTagData('username')
            if query.getTag('password'):
                password = query.getTagData('password')
            if query.getTag('misc'):
                clientid = query.getTagData('misc')
                clientid = clientid.strip().split(' ')[-1]
            if query.getTag('remove'):
               remove = True
            if not remove and username and password and clientid:
                if userfile.has_key(fromjid):
                    conf = userfile[fromjid]
                else:
                    if not config.allowRegister:
                        return
                    conf = {}
                conf['username']=username
                conf['password']=password
                conf['clientid']=clientid
                userfile[fromjid]=conf
                userfile.sync()
                m=event.buildReply('result')
                self.jabberqueue(m)
                if self.userlist.has_key(fromjid):
                    self.mxit_closed(self.userlist[fromjid])
                if not self.userlist.has_key(fromjid):
                    mxitobj = mxitlib.MXitCon(username.encode('utf-8'),password.encode('utf-8'),conf['clientid'].encode('utf-8'), fromjid,config.host,config.dumpProtocol)
                    self.userlist[fromjid]=mxitobj
                    if config.dumpProtocol: print "try connect"
                    s = mxitobj.connect()
                    if s != None:
                        if config.dumpProtocol: print "conect made"
                        rdsocketlist[s]=mxitobj
                        self.userlist[fromjid]=mxitobj
                        self.mxitqueue(fromjid,mxitobj.mxit_send_login())
                    mxitobj.handlers['login']=self.mxit_reg_login
                    mxitobj.handlers['loginfail']=self.mxit_reg_loginfail
                    mxitobj.handlers['closed']=self.mxit_reg_loginfail
                    mxitobj.event = event
                    mxitobj.showstatus = None
                    mxitobj.away = None
            elif remove and not username and not password and not clientid:
                if self.userlist.has_key(fromjid):
                    self.mxit_closed(self.userlist[fromjid])
                if userfile.has_key(fromjid):
                    del userfile[fromjid]
                    userfile.sync()
                    m = event.buildReply('result')
                    self.jabberqueue(m)
                    m = Presence(to = event.getFrom(), frm = config.jid, typ = 'unsubscribe')
                    self.jabberqueue(m)
                    m = Presence(to = event.getFrom(), frm = config.jid, typ = 'unsubscribed')
                    self.jabberqueue(m)
                else:
                    self.jabberqueue(Error(event,ERR_BAD_REQUEST))
            else:
                self.jabberqueue(Error(event,ERR_BAD_REQUEST))
        else:
            self.jabberqueue(Error(event,ERR_BAD_REQUEST))
        raise NodeProcessed

    def xmpp_iq_gateway_get(self, con, event):
        if event.getTo() == config.jid:
            m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result', queryNS=NS_GATEWAY, payload=[
                Node('desc',payload='Please enter the MXit ID of the person you would like to contact.'),
                Node('prompt',payload='MXit ID')])
            m.setID(event.getID())
            self.jabberqueue(m)
            raise NodeProcessed

    def xmpp_iq_gateway_set(self, con, event):
        if event.getTo() == config.jid:
            query = event.getTag('query')
            jid = query.getTagData('prompt')
            m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result', queryNS=NS_GATEWAY, payload=[
                Node('jid',payload='%s@%s'%(MXitIDEncode(jid),config.jid)),     # JEP-0100 says use jid,
                Node('prompt',payload='%s@%s'%(MXitIDEncode(jid),config.jid))]) # but Psi uses prompt
            m.setID(event.getID())
            self.jabberqueue(m)
            raise NodeProcessed

    def xmpp_iq_vcard(self, con, event):
        fromjid = event.getFrom()
        fromstripped = fromjid.getStripped().encode('utf-8')
        if userfile.has_key(fromstripped):
            if event.getTo().getDomain() == config.jid:
                mxitid = MXitIDDecode(event.getTo().getNode())
            else:
                self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
            m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result')
            m.setID(event.getID())
            v = m.addChild(name='vCard', namespace=NS_VCARD)
            nick = mxitid
            groups = []
            for each in self.userlist[fromstripped].buddylist.keys():
                for (buddymxitid,buddynick) in self.userlist[fromstripped].buddylist[each]:
                    if mxitid == buddymxitid:
                        nick = buddynick
                        groups.append(each)
            v.setTagData(tag='NICKNAME', val=nick)
            v.setTagData(tag='ROLE', val=','.join(groups))            
            if userfile[fromstripped].has_key('avatar') and \
                userfile[fromstripped]['avatar'].has_key(mxitid):
                p = v.addChild(name='PHOTO')
                p.setTagData(tag='TYPE', val='image/png')
                p.setTagData(tag='BINVAL', val=base64.encodestring(userfile[fromstripped]['avatar'][mxitid][1]))
            self.jabberqueue(m)
        else:
            self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
        raise NodeProcessed

    def mxit_closed(self, mxitobj):
        if self.userlist.has_key(mxitobj.fromjid):
            if not mxitobj.connok:
                if config.dumpProtocol: print "got closed, on not connok"
                if mxitobj.moreservers():
                    if rdsocketlist.has_key(mxitobj.sock):
                        del rdsocketlist[mxitobj.sock]
                    if wrsocketlist.has_key(mxitobj.sock):
                        del wrsocketlist[mxitobj.sock]
                    mxitobj.sock.close()
                    s= mxitobj.connect()
                    if s != None:
                        rdsocketlist[s]=mxitobj
                        self.userlist[mxitobj.fromjid]=mxitobj
                        self.mxitqueue(mxitobj.fromjid,mxitobj.mxit_send_login())
                        return # this method terminates here - all change please
                else:
                    self.mxit_loginfail(mxitobj)
            self.mxit_send_offline(mxitobj.fromjid)
            if self.userlist.has_key(mxitobj.fromjid):
                if self.userlist[mxitobj.fromjid].away != 'unavailable':
                    self.jabberqueue(Error(Presence(frm = mxitobj.fromjid, to = config.jid),ERR_REMOTE_SERVER_TIMEOUT))
                del self.userlist[mxitobj.fromjid]
            if rdsocketlist.has_key(mxitobj.sock):
                del rdsocketlist[mxitobj.sock]
            if wrsocketlist.has_key(mxitobj.sock):
                del wrsocketlist[mxitobj.sock]
            if mxitobj.sock:
                mxitobj.sock.close()
            del mxitobj

    def mxit_login(self,mxitobj):
        if config.dumpProtocol: print "got login"
        for each in mxitobj.xresources.keys():
            mjid = JID(mxitobj.fromjid)
            mjid.setResource(each)
            self.jabberqueue(Presence(to = mjid, frm = config.jid))
        mxitobj.handlers['loginfail']= self.mxit_loginfail
        mxitobj.handlers['login']= self.mxit_closed
        mxitobj.connok = True
        self.mxitqueue(mxitobj.fromjid,mxitobj.mxit_send_online(mxitobj.away, mxitobj.showstatus))
        if userfile[mxitobj.fromjid]['username'] != mxitobj.username:
            conf = userfile[mxitobj.fromjid]
            conf['username']=mxitobj.username
            userfile[mxitobj.fromjid]=conf
            self.jabberqueue(Message(to=mxitobj.fromjid,frm=config.jid,subject='MXit login name',body='Your MXit username was specified incorrectly in the configuration. This may be because of an upgrade from a previous version, the configuration has been updated'))

    def mxit_loginfail(self,mxitobj, reason = None):
        if config.dumpProtocol: print "got login fail: ",reason
        self.jabberqueue(Message(to=mxitobj.event.getFrom(),frm=config.jid,subject='Login Failure',body='Login Failed to MXit service. %s'%reason))
        self.jabberqueue(Error(mxitobj.event,ERR_NOT_AUTHORIZED))
        del self.userlist[mxitobj.fromjid]
        if rdsocketlist.has_key(mxitobj.sock):
            del rdsocketlist[mxitobj.sock]
        if wrsocketlist.has_key(mxitobj.sock):
            del wrsocketlist[mxitobj.sock]
        mxitobj.sock.close()
        del mxitobj

    def mxit_online(self,mxitobj,mxitid):
        #print mxitobj.xresources.keys()
        for each in mxitobj.xresources.keys():
            mjid = JID(mxitobj.fromjid)
            mjid.setResource(each)
            #print mjid, each
            b = Presence(to = mjid, frm = '%s@%s/mxit'%(MXitIDEncode(mxitid), config.jid),priority = 10, show=mxitobj.roster[mxitid][1])
            b.addChild(node=Node(NODE_VCARDUPDATE,payload=[Node('nickname',payload=mxitobj.roster[mxitid][2])]))
            self.jabberqueue(b)

    def mxit_offline(self,mxitobj,mxitid):
        for each in mxitobj.xresources.keys():
            mjid = JID(mxitobj.fromjid)
            mjid.setResource(each)
            self.jabberqueue(Presence(to=mjid, frm = '%s@%s/mxit'%(MXitIDEncode(mxitid), config.jid),typ='unavailable'))

    def mxit_subscribe(self,mxitobj,mxitid,msg):
        self.jabberqueue(Presence(typ='subscribe',frm = '%s@%s' % (MXitIDEncode(mxitid), config.jid), to=mxitobj.fromjid,payload=msg))

    def mxit_message(self,mxitobj,mxitid,msg,timestamp):
        m = Message(typ='chat',frm = '%s@%s/mxit' %(MXitIDEncode(mxitid),config.jid), to=mxitobj.fromjid,body=msg)
        self.jabberqueue(m)

    def mxit_messagefail(self,mxitobj,mxitid,msg):
        self.jabberqueue(Error(Message(typ='chat',to = '%s@%s' %(MXitIDEncode(mxitid),config.jid), frm=mxitobj.fromjid,body=msg),ERR_SERVICE_UNAVAILABLE))

    def mxit_reg_login(self,mxitobj):
        # registration login handler
        if config.dumpProtocol: print "got reg login"
        #m = mxitobj.event.buildReply('result')
        #self.jabberqueue(m)
        mxitobj.connok = True
        self.jabberqueue(Presence(to=mxitobj.event.getFrom(),frm=mxitobj.event.getTo(),typ=mxitobj.event.getType()))
        self.jabberqueue(Presence(typ='subscribe',to=mxitobj.fromjid, frm=config.jid))

    def mxit_reg_loginfail(self,mxitobj,reason = None):
        if config.dumpProtocol: print "got reg login fail: ",reason
        if mxitobj.moreservers() and reason != None:
            if rdsocketlist.has_key(mxitobj.sock):
                del rdsocketlist[mxitobj.sock]
            if wrsocketlist.has_key(mxitobj.sock):
                del wrsocketlist[mxitobj.sock]
            mxitobj.sock.close()
            s= mxitobj.connect()
            if s != None:
                rdsocketlist[s]=mxitobj
                self.userlist[mxitobj.fromjid]=mxitobj
                self.mxitqueue(mxitobj.fromjid,mxitobj.mxit_send_login())
                return # this method terminates here - all change please
        # registration login failure handler
        self.jabberqueue(Message(to=mxitobj.event.getFrom(),frm=config.jid,subject='Registration Failure',body='Login Failed to MXit service. %s'%reason))
        self.jabberqueue(Error(mxitobj.event,ERR_NOT_ACCEPTABLE)) # will not work, no event object
        del self.userlist[mxitobj.fromjid]
        if rdsocketlist.has_key(mxitobj.sock):
            del rdsocketlist[mxitobj.sock]
        if wrsocketlist.has_key(mxitobj.sock):
            del wrsocketlist[mxitobj.sock]
        mxitobj.sock.close()
        del mxitobj

    def mxit_send_online(self,fromjid,resource=None):
        #if config.dumpProtocol: print fromjid,self.userlist[fromjid].roster
        fromstripped = fromjid
        if resource != None:
            fromjid = JID(fromjid)
            fromjid.setResource(resource)
        self.jabberqueue(Presence(to=fromjid,frm = config.jid))
        for mxitid in self.userlist[fromstripped].roster:
            if self.userlist[fromstripped].roster[mxitid][0] == 'available':
                self.jabberqueue(Presence(frm = '%s@%s/mxit' % (MXitIDEncode(mxitid),config.jid), to = fromjid))

    def mxit_send_offline(self,fromjid,resource=None,status=None):
        #if config.dumpProtocol and self.userlist.has_key(fromjid): print fromjid,self.userlist[fromjid].roster
        fromstripped = fromjid
        if resource != None:
            fromjid = JID(fromjid)
            fromjid.setResource(resource)
        self.jabberqueue(Presence(to=fromjid,frm = config.jid, typ='unavailable',status=status))
        if self.userlist.has_key(fromstripped):
            for mxitid in self.userlist[fromstripped].roster:
                if self.userlist[fromstripped].roster[mxitid][0] == 'available':
                    self.jabberqueue(Presence(frm = '%s@%s/mxit' % (MXitIDEncode(mxitid),config.jid), to = fromjid, typ='unavailable'))

    def xmpp_iq_version(self, con, event):
        fromjid = event.getFrom()
        to = event.getTo()
        id = event.getID()
        uname = platform.uname()
        m = Iq(to = fromjid, frm = to, typ = 'result', queryNS=NS_VERSION, payload=[Node('name',payload=VERSTR), Node('version',payload=version),Node('os',payload=('%s %s %s' % (uname[0],uname[2],uname[4])).strip())])
        m.setID(id)
        self.jabberqueue(m)
        raise NodeProcessed

    def xmpp_connect(self):
        connected = self.jabber.connect((config.mainServer,config.port))
        if config.dumpProtocol: print "connected:",connected
        while not connected:
            time.sleep(5)
            connected = self.jabber.connect((config.mainServer,config.port))
            if config.dumpProtocol: print "connected:",connected
        self.register_handlers()
        if config.dumpProtocol: print "trying auth"
        connected = self.jabber.auth(config.saslUsername,config.secret)
        if config.dumpProtocol: print "auth return:",connected
        return connected

    def xmpp_disconnect(self):
        for each in self.userlist.keys():
            mxitobj=self.userlist[each]
            del self.userlist[mxitobj.fromjid]
            if rdsocketlist.has_key(mxitobj.sock):
                del rdsocketlist[mxitobj.sock]
            if wrsocketlist.has_key(mxitobj.sock):
                del wrsocketlist[mxitobj.sock]
            mxitobj.sock.close()
            del mxitobj
        del rdsocketlist[self.jabber.Connection._sock]
        if wrsocketlist.has_key(self.jabber.Connection._sock):
            del wrsocketlist[self.jabber.Connection._sock]
        time.sleep(5)
        while not self.jabber.reconnectAndReauth():
            time.sleep(5)
        rdsocketlist[self.jabber.Connection._sock]='xmpp'

def loadConfig():
    configOptions = {}
    for configFile in config.configFiles:
        if os.path.isfile(configFile):
            xmlconfig.reloadConfig(configFile, configOptions)
            config.configFile = configFile
            return
    print "Configuration file not found. You need to create a config file and put it in one of these locations:\n    " + "\n    ".join(config.configFiles)
    sys.exit(1)

def logError():
    err = '%s - %s\n'%(time.strftime('%a %d %b %Y %H:%M:%S'),version)
    if logfile != None:
        logfile.write(err)
        traceback.print_exc(file=logfile)
        logfile.flush()
    sys.stderr.write(err)
    traceback.print_exc()
    sys.exc_clear()

def sigHandler(signum, frame):
    #transport.offlinemsg = 'Signal handler called with signal %s'%signum
    transport.online = 0

if __name__ == '__main__':
    if 'PID' in os.environ:
        config.pid = os.environ['PID']
    loadConfig()
    if config.pid:
        pidfile = open(config.pid,'w')
        pidfile.write(`os.getpid()`)
        pidfile.close()

    if config.saslUsername:
        sasl = 1
    else:
        config.saslUsername = config.jid
        sasl = 0

    userfile = shelve.open(config.spoolFile)
    logfile = None
    if config.debugFile:
        logfile = open(config.debugFile,'a')

    if config.dumpProtocol:
        debug=['always', 'nodebuilder']
    else:
        debug=[]
    connection = xmpp.client.Component(config.jid,config.port,debug=debug,sasl=sasl,bind=config.useComponentBinding,route=config.useRouteWrap)
    transport = Transport(connection)
    if not transport.xmpp_connect():
        print "Could not connect to server, or password mismatch!"
        sys.exit(1)
    # Set the signal handlers
    signal.signal(signal.SIGINT, sigHandler)
    signal.signal(signal.SIGTERM, sigHandler)
    rdsocketlist[connection.Connection._sock]='xmpp'
    while transport.online:
        #print 'poll',rdsocketlist
        try:
            (i , o, e) = select.select(rdsocketlist.keys(),wrsocketlist.keys(),[],1)
        except socket.error:
            print "Bad Socket", rdsocketlist, wrsocketlist
            logError()
            transport.findbadconn()
            sys.exc_clear()
            (i , o, e) = select.select(rdsocketlist.keys(),wrsocketlist.keys(),[],1)
        except select.error:
            sys.exc_clear()
            (i , o, e) = select.select(rdsocketlist.keys(),wrsocketlist.keys(),[],1)
        for each in i:
            #print 'reading',each,rdsocketlist.has_key(each)
            if rdsocketlist.has_key(each):
                if rdsocketlist[each] == 'xmpp':
                    try:
                        connection.Process(1)
                    except IOError:
                        transport.xmpp_disconnect()
                    except:
                        logError()
                    if not connection.isConnected():  transport.xmpp_disconnect()
                else:
                    try:
                        rdsocketlist[each].Process()
                    except socket.error:
                        transport.mxit_closed(rdsocketlist[each])
                    except:
                        logError()
        for each in o:
            #print 'writing',each,rdsocketlist.has_key(each),wrsocketlist.has_key(each)
            if rdsocketlist.has_key(each) and wrsocketlist.has_key(each):
                try:
                    if rdsocketlist[each] == 'xmpp':
                        while select.select([],[each],[])[1] and wrsocketlist[each] != []:
                            connection.send(wrsocketlist[each].pop(0))
                    else:
                        #print wrsocketlist
                        packet = wrsocketlist[each].pop(0)
                        if config.dumpProtocol: mxitlib.printpacket(packet)
                        each.send(packet)
                    if wrsocketlist[each] == []:
                        del wrsocketlist[each]
                except socket.error:
                    transport.mxit_closed(rdsocketlist[each])
                except:
                    logError()
            else:
                #print 'not writing',each,rdsocketlist.has_key(each),wrsocketlist.has_key(each)
                if rdsocketlist.has_key(each):
                    del rdsocketlist[each]
                if wrsocketlist.has_key(each):
                    del wrsocketlist[each]
        #delayed execution method modified from python-irclib written by Joel Rosdahl <joel@rosdahl.net>
        for each in timerlist:
            #print int(time.time())%each[0]-each[1]
            if not (int(time.time())%each[0]-each[1]):
                try:
                    apply(each[2],each[3])
                except:
                    logError()
    for each in [x for x in transport.userlist.keys()]:
        transport.userlist[each].connok = True
        transport.mxit_send_offline(each, status = transport.offlinemsg)
    del rdsocketlist[connection.Connection._sock]
    if wrsocketlist.has_key(connection.Connection._sock):
        while wrsocketlist[connection.Connection._sock] != []:
            connection.send(wrsocketlist[connection.Connection._sock].pop(0))
        del wrsocketlist[connection.Connection._sock]
    userfile.close()
    connection.disconnect()
    if config.pid:
        os.unlink(config.pid)
    if logfile:
        logfile.close()
    if transport.restart:
        args=[sys.executable]+sys.argv
        if os.name == 'nt': args = ["\"%s\"" % a for a in args]
        if config.dumpProtocol: print sys.executable, args
        os.execv(sys.executable, args)
