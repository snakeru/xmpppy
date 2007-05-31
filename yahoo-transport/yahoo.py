#! /usr/bin/env python
# $Id$
version = 'CVS ' + '$Revision$'.split()[1]
#
# Yahoo! Transport
# June 2004 Copyright (c) Mike Albon
# 2006 Copyright (c) Norman Rasmussen
#
# This program is free software licensed with the GNU Public License Version 2.
# For a full copy of the license please go here http://www.gnu.org/licenses/licenses.html#GPL

import base64, ConfigParser, os, platform, re, select, sha, shelve, signal, socket, sys, time, traceback
import xmpp.client
from curphoo import cpformat
from xmpp.protocol import *
from xmpp.browser import *
from xmpp.jep0106 import *
import config, roomlist, xmlconfig, ylib
from adhoc import AdHocCommands
from toolbox import *

VERSTR = 'Yahoo! Transport'
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

def YIDEncode(yid):
    return yid.replace('@','%')

def YIDDecode(yid):
    return yid.replace('%','@')

roomenccodere = re.compile('([^-]?)([A-Z-])')
def RoomEncode(yid):
    return JIDEncode(roomenccodere.sub('\\1-\\2', yid))

roomdeccodere = re.compile('-([a-zA-Z-])')
def RoomDecode(yid):
    def decode(m):
        return m.group(1).upper()
    return roomdeccodere.sub(decode, JIDDecode(yid))

class Transport:

    # This class is the main collection of where all the handlers for both the Yahoo and Jabber

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

    def yahooqueue(self,fromjid,packet):
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
                self.y_closed(self.userlist[each])
            else:
                try:
                    a,b,c = select.select([self.userlist[each].sock],[self.userlist[each].sock],[self.userlist[each].sock],0)
                except:
                    self.y_closed(self.userlist[each])
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
        self.jabber.RegisterHandler('iq',self.xmpp_iq_avatar, typ = 'get', ns=NS_AVATAR)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_gateway_get, typ = 'get', ns=NS_GATEWAY)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_gateway_set, typ = 'set', ns=NS_GATEWAY)
        self.jabber.RegisterHandler('iq',self.xmpp_iq_vcard, typ = 'get', ns=NS_VCARD)
        #self.jabber.RegisterHandler('iq',self.xmpp_iq_notimplemented)
        #self.jabber.RegisterHandler('iq',self.xmpp_iq_mucadmin_set,typ = 'set', ns=NS_MUC_ADMIN)
        #self.jabber.RegisterHandler('iq',self.xmpp_iq_mucadmin_get,typ = 'get', ns=NS_MUC_ADMIN)
        self.disco = Browser()
        self.disco.PlugIn(self.jabber)
        self.adhoccommands = AdHocCommands(userfile)
        self.adhoccommands.PlugIn(self)
        self.disco.setDiscoHandler(self.xmpp_base_disco,node='',jid=config.jid)
        self.disco.setDiscoHandler(self.xmpp_base_disco,node='',jid=config.confjid)
        self.disco.setDiscoHandler(self.xmpp_base_disco,node='',jid='')

    def register_ymsg_handlers(self, con):
        con.handlers['online']= self.y_online
        con.handlers['offline']= self.y_offline
        con.handlers['chatonline']= self.y_chatonline
        con.handlers['chatoffline']= self.y_chatoffline
        con.handlers['login'] = self.y_login
        con.handlers['logout'] = self.y_loginfail
        con.handlers['loginfail'] = self.y_loginfail
        con.handlers['subscribe'] = self.y_subscribe
        con.handlers['message'] = self.y_message
        con.handlers['messagefail'] = self.y_messagefail
        con.handlers['chatmessage'] = self.y_chatmessage
        con.handlers['notify'] = self.y_notify
        con.handlers['ping'] = self.y_ping
        con.handlers['calendar'] = self.y_calendar
        con.handlers['email'] = self.y_email
        con.handlers['closed'] = self.y_closed
        con.handlers['avatar'] = self.y_avatar
        #chatroom handlers
        con.handlers['reqroom'] = self.y_chat_login
        con.handlers['roominfo'] = self.y_chat_roominfo
        con.handlers['chatjoin'] = self.y_chat_join
        con.handlers['chatleave'] = self.y_chat_leave
        con.handlers['roommessage'] = self.y_roommessage
        #con.handlers['roommessagefail'] = self.y_roommessagefail

    def xmpp_message(self, con, event):
        resource = 'messenger'
        fromjid = event.getFrom()
        if fromjid == None:
            return
        fromstripped = fromjid.getStripped().encode('utf8')
        if event.getTo().getNode() != None:
            if self.userlist.has_key(fromstripped):
                yobj=self.userlist[fromstripped]
                if event.getTo().getDomain() == config.jid:
                    yid = YIDDecode(event.getTo().getNode())
                    yidenc = yid.encode('utf-8')
                    if event.getBody() == None:
                        xevent = event.getTag('x',namespace=NS_EVENT)
                        if xevent:
                            state = '0'
                            for events in xevent.getChildren():
                                if events.getName() == 'composing':
                                    state = '1'
                            self.yahooqueue(fromstripped,yobj.ymsg_send_notify(yidenc,state))
                        return
                    resource = 'messenger'
                    # normal non-groupchat or conference cases
                    if resource == 'messenger':
                        if event.getType() == None or event.getType() =='normal':
                            # normal message case
                            #print 'got message'
                            self.yahooqueue(fromstripped,yobj.ymsg_send_message(yidenc,event.getBody().encode('utf-8')))
                        elif event.getType() == 'chat':
                            # normal chat case
                            #print 'got message'
                            self.yahooqueue(fromstripped,yobj.ymsg_send_message(yidenc,event.getBody().encode('utf-8')))
                        else:
                            #print 'type error'
                            self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                    elif resource == 'chat':
                        if event.getType() == None or event.getType() =='normal':
                            # normal message case
                            #print 'got message'
                            self.yahooqueue(fromstripped,yobj.ymsg_send_chatmessage(yidenc,event.getBody().encode('utf-8')))
                        elif event.getType() == 'chat':
                            # normal chat case
                            #print 'got message'
                            self.yahooqueue(fromstripped,yobj.ymsg_send_chatmessage(yidenc,event.getBody().encode('utf-8')))
                        else:
                            #print 'type error'
                            self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                    else:
                        #print 'resource error'
                        self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                elif config.enableChatrooms and event.getTo().getDomain() == config.confjid:
                    if event.getBody() == None:
                        return
                    yid = RoomDecode(event.getTo().getNode())
                    # Must add resource matching here, ie only connected resource can send to room.
                    if event.getSubject():
                        self.jabberqueue(Error(event,ERR_NOT_IMPLEMENTED))
                        return
                    if event.getTo().getResource() == None or event.getTo().getResource() == '':
                        #print yobj.roomlist, yobj.roomnames
                        if yobj.roomnames.has_key(yid.lower()):
                            room = yobj.roomnames[yid.lower()].encode('utf-8')
                        else:
                            room = None
                        if config.dumpProtocol: print "groupchat room: ",room
                        if room != None:
                            if event.getBody()[0:3] == '/me':
                                type = 2
                                body = event.getBody()[4:].encode('utf-8')
                            else:
                                type = 1
                                body = event.getBody().encode('utf-8')
                            self.yahooqueue(fromstripped,yobj.ymsg_send_roommsg(room,body,type))
                            to = '%s/%s'%(event.getTo(),yobj.username)
                            self.jabberqueue(Message(to=event.getFrom(), frm= to, typ='groupchat',body=event.getBody()))
                        else:
                            self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                else:
                    self.jabberqueue(Error(event,ERR_BAD_REQUEST))
            else:
                if config.dumpProtocol: print 'no item error'
                self.jabberqueue(Error(event,ERR_REGISTRATION_REQUIRED))
        else:
            self.jabberqueue(Error(event,ERR_BAD_REQUEST))

    def xmpp_presence(self, con, event):
        yobj = None
        yrost = None
        fromjid = event.getFrom()
        fromstripped = fromjid.getStripped().encode('utf8')
        if userfile.has_key(fromstripped):
            if event.getTo().getDomain() == config.jid:
                yid = YIDDecode(event.getTo().getNode())
                yidenc = yid.encode('utf-8')
                if event.getType() == 'subscribed':
                    if self.userlist.has_key(fromstripped):
                        yobj=self.userlist[fromstripped]
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
                                m = Message(to = fromjid, frm = config.jid, subject= 'Yahoo Roster Items', body = 'Items from Yahoo Roster')
                                p=None
                                p= m.setTag('x',namespace = NS_ROSTERX)
                                yrost = yobj.buddylist
                                if config.dumpProtocol: print yrost
                                for each in yrost.keys():
                                    for yid in yrost[each]:
                                        p.addChild(name='item', attrs={'jid':'%s@%s'%(YIDEncode(yid),config.jid),'name':yid, 'action':'add'},payload=[Node('group',payload=each)])
                                self.jabberqueue(m)
                                if config.dumpProtocol: print m
                            else:
                                for each in yobj.buddylist.keys():
                                    for yid in yobj.buddylist[each]:
                                        self.jabberqueue(Presence(frm='%s@%s'%(YIDEncode(yid),config.jid),to = fromjid, typ='subscribe', status='Yahoo messenger contact'))
                            m = Presence(to = fromjid, frm = config.jid)
                            self.jabberqueue(m)
                            self.y_send_online(fromstripped)
                            self.register_ymsg_handlers(yobj)
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'subscribe':
                    if self.userlist.has_key(fromstripped):
                        yobj=self.userlist[fromstripped]
                        if event.getTo() == config.jid:
                            conf = userfile[fromstripped]
                            conf['usubscribed']=True
                            userfile[fromstripped]=conf
                            userfile.sync()
                            m = Presence(to = fromjid, frm = config.jid, typ = 'subscribed')
                            self.jabberqueue(m)
                        elif yobj.roster.has_key(yidenc):
                            m = Presence(to = fromjid, frm = event.getTo(), typ = 'subscribed')
                            self.jabberqueue(m)
                        else:
                            #add new user case.
                            if event.getStatus() != None:
                                if config.dumpProtocol: print event.getStatus().encode('utf-8')
                                status = event.getStatus().encode('utf-8')
                            else:
                                status = ''
                            self.yahooqueue(fromstripped,yobj.ymsg_send_addbuddy(yidenc, status))
                            self.jabberqueue(Presence(frm=event.getTo(), to = event.getFrom(), typ = 'subscribed'))
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'unsubscribe':
                    if self.userlist.has_key(fromstripped):
                        yobj=self.userlist[fromstripped]
                        if yobj.roster.has_key(yid):
                            if event.getStatus() != None:
                                msg = event.getStatus().encode('utf-8')
                            else:
                                msg = ''
                            self.yahooqueue(fromstripped,yobj.ymsg_send_delbuddy(yidenc, msg))
                            self.jabberqueue(Presence(frm=event.getTo(), to = event.getFrom(), typ = 'unsubscribed'))
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'unsubscribed':
                    # should do something more elegant here
                    pass
                elif event.getType() == None or event.getType() == 'available' or event.getType() == 'invisible':
                    # code to add yahoo connection goes here
                    if yid != '':
                        return
                    if self.userlist.has_key(fromstripped):
                        yobj=self.userlist[fromstripped]
                        # update status case and additional resource case
                        # update status case
                        if yobj.xresources.has_key(event.getFrom().getResource()):
                            #update resource record
                            yobj.xresources[event.getFrom().getResource()]=(event.getShow(),event.getPriority(),event.getStatus(),yobj.xresources[event.getFrom().getResource()][3])
                            if config.dumpProtocol: print "Update resource login: %s" % yobj.xresources
                        else:
                            #new resource login
                            yobj.xresources[event.getFrom().getResource()]=(event.getShow(),event.getPriority(),event.getStatus(),time.time())
                            if config.dumpProtocol: print "New resource login: %s" % yobj.xresources
                            #send roster as is
                            self.y_send_online(fromstripped,event.getFrom().getResource())
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
                        yobj = ylib.YahooCon(conf['username'].encode('utf-8'),conf['password'].encode('utf-8'), fromstripped,config.host,config.dumpProtocol)
                        s = yobj.connect()
                        if s != None:
                            rdsocketlist[s]=yobj
                            self.userlist[fromstripped]=yobj
                            self.register_ymsg_handlers(yobj)
                            self.yahooqueue(fromstripped,yobj.ymsg_send_init())
                            yobj.event = event
                            if event.getShow() == 'xa' or event.getShow() == 'away':
                                yobj.away = 'away'
                            elif event.getShow() == 'dnd':
                                yobj.away = 'dnd'
                            elif event.getShow() == 'invisible':
                                yobj.away = 'invisible'
                            else:
                                yobj.away = None
                            yobj.showstatus = event.getStatus()
                            #Add line into currently matched resources
                            yobj.xresources[event.getFrom().getResource()]=(event.getShow(),event.getPriority(),event.getStatus(),time.time())
                        else:
                            self.jabberqueue(Error(event,ERR_REMOTE_SERVER_TIMEOUT))
                elif event.getType() == 'unavailable':
                    # Match resources and remove the newly unavailable one
                    if self.userlist.has_key(fromstripped):
                        yobj=self.userlist[fromstripped]
                        #print 'Resource: ', event.getFrom().getResource(), "To Node: ",yid
                        if yid =='':
                            self.y_send_offline(fromstripped,event.getFrom().getResource())
                            if yobj.xresources.has_key(event.getFrom().getResource()):
                                del yobj.xresources[event.getFrom().getResource()]
                                self.xmpp_presence_do_update(event,fromstripped)
                            #Single resource case
                            #print yobj.xresources
                            if yobj.xresources == {}:
                                if config.dumpProtocol: print 'No more resource logins'
                                if yobj.pripingobj in timerlist:
                                    timerlist.remove(yobj.pripingobj)
                                if yobj.secpingobj in timerlist:
                                    timerlist.remove(yobj.secpingobj)
                                del self.userlist[yobj.fromjid]
                                if rdsocketlist.has_key(yobj.sock):
                                    del rdsocketlist[yobj.sock]
                                if wrsocketlist.has_key(yobj.sock):
                                    del wrsocketlist[yobj.sock]
                                yobj.sock.close()
                                del yobj
                    else:
                        self.jabberqueue(Presence(to=fromjid,frm = config.jid, typ='unavailable'))
            elif config.enableChatrooms and event.getTo().getDomain() == config.confjid:
                yid = RoomDecode(event.getTo().getNode())
                yidenc = yid.encode('utf-8')
                #Need to move Chatpings into this section for Yahoo rooms.
                if self.userlist.has_key(fromstripped):
                    yobj=self.userlist[fromstripped]
                    if yobj.connok:
                        if config.dumpProtocol: print "chat presence"
                        yobj.roomnames[yid.lower()] = yid
                        if event.getType() == 'available' or event.getType() == None or event.getType() == '':
                            nick = event.getTo().getResource()
                            yobj.nick = nick
                            if not yobj.chatlogin:
                                self.yahooqueue(fromstripped,yobj.ymsg_send_conflogon())
                                self.yahooqueue(fromstripped,yobj.ymsg_send_chatlogin(None))
                                yobj.chatresource = event.getFrom().getResource()
                                #Add secondary ping object code
                                freq = 5 * 60 #Secondary ping frequency from Zinc
                                offset = int(time.time())%freq
                                yobj.confpingtime = time.time()
                                yobj.confpingobj=(freq,offset,self.yahooqueue,[yobj.fromjid, yobj.ymsg_send_confping()])
                                timerlist.append(yobj.confpingobj)
                                yobj.roomtojoin = yidenc
                            else:
                                self.yahooqueue(fromstripped,yobj.ymsg_send_chatjoin(yidenc))
                        elif event.getType() == 'unavailable':
                            # Must add code to compare from resources here
                            self.yahooqueue(fromstripped,yobj.ymsg_send_chatleave(yidenc))
                            self.yahooqueue(fromstripped,yobj.ymsg_send_chatlogout())
                            self.yahooqueue(fromstripped,yobj.ymsg_send_conflogoff())
                            if 'confpingobj' in dir(yobj) and yobj.confpingobj in timerlist:
                                timerlist.remove(yobj.confpingobj)
                        else:
                            self.jabberqueue(Error(event,ERR_FEATURE_NOT_IMPLEMENTED))
                    else:
                        self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                else:
                    self.jabberqueue(Error(event,ERR_BAD_REQUEST))
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
        yobj=self.userlist[fromstripped]
        for each in yobj.xresources.keys():
            #print each,yobj.xresources
            if yobj.xresources[each][1]>priority:
                #if priority is higher then take the highest
                age = yobj.xresources[each][3]
                priority = yobj.xresources[each][1]
                resource = each
            elif yobj.xresources[each][1]==priority:
                #if priority is the same then take the oldest
                if yobj.xresources[each][3]<age:
                    age = yobj.xresources[each][3]
                    priority = yobj.xresources[each][1]
                    resource = each
        if resource == event.getFrom().getResource():
            #only update shown status if resource is current datasource
            if event.getShow() == None:
                if event.getStatus() != None:
                    self.yahooqueue(fromstripped,yobj.ymsg_send_away(None,event.getStatus()))
                else:
                    self.yahooqueue(fromstripped,yobj.ymsg_send_back())
                yobj.away = None
            elif event.getShow() == 'xa' or event.getShow() == 'away':
                self.yahooqueue(fromstripped, yobj.ymsg_send_away('away',event.getStatus()))
                yobj.away = 'away'
            elif event.getShow() == 'dnd':
                self.yahooqueue(fromstripped, yobj.ymsg_send_away('dnd',event.getStatus()))
                yobj.away= 'dnd'
            elif event.getType() == 'invisible':
                self.yahooqueue(fromstripped, yobj.ymsg_send_away('invisible',None))
                yobj.away= 'invisible'

    def xmpp_iq_notimplemented(self, con, event):
        self.jabberqueue(Error(event,ERR_FEATURE_NOT_IMPLEMENTED))


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
                            {'category':'gateway','type':'yahoo','name':VERSTR}],
                        'features':features}
                if type == 'items':
                    list = [
                        {'node':NODE_ROSTER,'name':config.discoName + ' Roster','jid':config.jid}]
                    if config.enableChatrooms:
                        list.append({'jid':config.confjid,'name':config.discoName + ' Chatrooms'})
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
                        for yid in self.userlist[fromstripped].roster.keys():
                            list.append({'jid':'%s@%s' %(YIDEncode(yid),config.jid),'name':yid})
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
                yid = YIDDecode(event.getTo().getNode())
                if type == 'info':
                    if self.userlist[fromstripped].roster.has_key(yid):
                        features = [NS_VCARD,NS_VERSION]
                        if userfile[fromstripped.encode('utf-8')].has_key('avatar'):
                            if userfile[fromstripped.encode('utf-8')]['avatar'].has_key(yid):
                                features.append(NS_AVATAR)
                        return {
                            'ids':[
                                {'category':'client','type':'yahoo','name':yid}],
                            'features':features}
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                if type == 'items':
                    if self.userlist[fromstripped].roster.has_key(yid):
                        return []
            else:
                self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
        elif config.enableChatrooms and to == config.confjid:
            if node == None:
                if type == 'info':
                    #if we return disco info for our subnodes when the server asks, then we get added to the server's item list
                    if fromstripped == config.mainServerJID:
                        raise NodeProcessed
                    return {
                        'ids':[
                            {'category':'conference','type':'yahoo','name':VERSTR + ' Chatrooms'}],
                        'features':[NS_MUC,NS_VERSION]}
                if type == 'items':
                    if self.chatcat[0][0] < (time.time() - (5*60)):
                        t = roomlist.getcata(0)
                        if t != None:
                            for each in t.keys():
                                self.chatcat[each] = (time.time(),t[each])
                    list = []
                    for each in self.chatcat[0][1]:
                        list.append({'jid':to,'node':each,'name':self.chatcat[0][1][each]})
                    return list
            else:
                if type == 'info':
                    if self.chatcat[0][1].has_key(node):
                        return {
                            'ids':[
                                {'name':self.chatcat[0][1][node]}],
                            'features':[]}
                if type == 'items':
                    # Do get room item
                    if not self.catlist.has_key(node):
                        t = roomlist.getrooms(node)
                        if t != None:
                            self.catlist[node] = (time.time(),t)
                    else:
                        if self.catlist[node][0] < (time.time() - 5*60):
                            t = roomlist.getrooms(node)
                            if t != None:
                                self.catlist[node] = (time.time(),t)
                    # Do get more categories
                    if not self.chatcat.has_key(node):
                        t = roomlist.getcata(node)
                        if t != None:
                            self.chatcat[node] = (time.time(),t)
                    else:
                        if self.chatcat[node][0] < (time.time() - 5*60):
                            t = roomlist.getcata(node)
                            if t != None:
                                self.chatcat[node] = (time.time(),t)
                    list = []
                    if len(node.split('/')) == 1:
                        #add catagories first
                        if self.chatcat.has_key(node):
                            for each in self.chatcat[node][1].keys():
                                if each != 0 and 0 in self.chatcat[node][1].keys():
                                    list.append({'jid':to,'node':each,'name':self.chatcat[node][1][0][each]})
                        # First level of nodes
                        for z in self.catlist[node][1].keys():
                            each = self.catlist[node][1][z]
                            if each.has_key('type'):
                                if each['type'] == 'yahoo':
                                    if each.has_key('rooms'):
                                        for c in each['rooms'].keys():
                                            n = RoomEncode('%s:%s' % (each['name'],c))
                                            list.append({'jid':'%s@%s'%(n,config.confjid),'name':'%s:%s'%(each['name'],c)})
                    return list
        elif config.enableChatrooms and to.getDomain() == config.confjid:
            if type == 'info':
                yid = RoomDecode(event.getTo().getNode())
                lobby,room = yid.split(':')
                result = {
                    'ids':[
                        {'category':'conference','type':'yahoo','name':yid}],
                    'features':[NS_MUC]}
                for node in self.catlist.keys():
                    if self.catlist[node][1].has_key(lobby):
                        t = self.catlist[node][1][lobby]
                        if t['rooms'].has_key(room):
                            data = {'muc#roominfo_description':t['name'],'muc#roominfo_subject':t['topic'],'muc#roominfo_occupants':t['rooms'][room]['users']}
                            info = DataForm(typ = 'result', data= data)
                            field = info.setField('FORM_TYPE')
                            field.setType('hidden')
                            field.setValue('http://jabber.org/protocol/muc#roominfo')
                            result['xdata'] = info
                return result
            if type == 'items':
                return []

    def xmpp_iq_discoinfo_results(self, con, event):
        self.discoresults[event.getFrom().getStripped().encode('utf8')]=event
        raise NodeProcessed

    def xmpp_iq_register_get(self, con, event):
        if event.getTo() == config.jid:
            username = []
            password = []
            fromjid = event.getFrom().getStripped().encode('utf8')
            queryPayload = [Node('instructions', payload = 'Please provide your Yahoo! username and password')]
            if userfile.has_key(fromjid):
                try:
                    username = userfile[fromjid]['username']
                    password = userfile[fromjid]['password']
                except:
                    pass
                queryPayload += [
                    Node('username',payload=username),
                    Node('password',payload=password),
                    Node('registered')]
            else:
                if not config.allowRegister:
                    return
                queryPayload += [
                    Node('username'),
                    Node('password')]
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
            if query.getTag('remove'):
               remove = True
            if not remove and username and password:
                if userfile.has_key(fromjid):
                    conf = userfile[fromjid]
                else:
                    if not config.allowRegister:
                        return
                    conf = {}
                conf['username']=username
                conf['password']=password
                userfile[fromjid]=conf
                userfile.sync()
                m=event.buildReply('result')
                self.jabberqueue(m)
                if self.userlist.has_key(fromjid):
                    self.y_closed(self.userlist[fromjid])
                if not self.userlist.has_key(fromjid):
                    yobj = ylib.YahooCon(username.encode('utf-8'),password.encode('utf-8'), fromjid,config.host,config.dumpProtocol)
                    self.userlist[fromjid]=yobj
                    if config.dumpProtocol: print "try connect"
                    s = yobj.connect()
                    if s != None:
                        if config.dumpProtocol: print "conect made"
                        rdsocketlist[s]=yobj
                        self.yahooqueue(fromjid,yobj.ymsg_send_challenge())
                    yobj.handlers['login']=self.y_reg_login
                    yobj.handlers['loginfail']=self.y_reg_loginfail
                    yobj.handlers['closed']=self.y_reg_loginfail
                    yobj.handlers['ping']=self.y_ping
                    yobj.event = event
                    yobj.showstatus = None
                    yobj.away = None
            elif remove and not username and not password:
                if self.userlist.has_key(fromjid):
                    self.y_closed(self.userlist[fromjid])
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

    def xmpp_iq_avatar(self, con, event):
        fromjid = event.getFrom()
        fromstripped = fromjid.getStripped().encode('utf-8')
        if userfile.has_key(fromstripped):
            if event.getTo().getDomain() == config.jid:
                yid = YIDDecode(event.getTo().getNode())
            elif config.enableChatrooms and event.getTo().getDomain() == config.confjid:
                yid = YIDDecode(event.getTo().getResource())
            else:
                self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
            if userfile[fromstripped].has_key('avatar'):
                if userfile[fromstripped]['avatar'].has_key(yid):
                    m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result', queryNS=NS_AVATAR, payload=[Node('data',attrs={'mimetype':'image/png'},payload=base64.encodestring(userfile[fromstripped]['avatar'][yid][1]))])
                    m.setID(event.getID())
                    self.jabberqueue(m)
                else:
                    self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
            else:
                self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
        else:
            self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
        raise NodeProcessed

    def xmpp_iq_gateway_get(self, con, event):
        if event.getTo() == config.jid:
            m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result', queryNS=NS_GATEWAY, payload=[
                Node('desc',payload='Please enter the Yahoo! ID of the person you would like to contact.'),
                Node('prompt',payload='Yahoo! ID')])
            m.setID(event.getID())
            self.jabberqueue(m)
            raise NodeProcessed

    def xmpp_iq_gateway_set(self, con, event):
        if event.getTo() == config.jid:
            query = event.getTag('query')
            jid = query.getTagData('prompt')
            m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result', queryNS=NS_GATEWAY, payload=[
                Node('jid',payload='%s@%s'%(YIDEncode(jid),config.jid)),     # JEP-0100 says use jid,
                Node('prompt',payload='%s@%s'%(YIDEncode(jid),config.jid))]) # but Psi uses prompt
            m.setID(event.getID())
            self.jabberqueue(m)
            raise NodeProcessed

    def xmpp_iq_vcard(self, con, event):
        fromjid = event.getFrom()
        fromstripped = fromjid.getStripped().encode('utf-8')
        if userfile.has_key(fromstripped):
            if event.getTo().getDomain() == config.jid:
                yid = YIDDecode(event.getTo().getNode())
            elif config.enableChatrooms and event.getTo().getDomain() == config.confjid:
                yid = YIDDecode(event.getTo().getResource())
            else:
                self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
            m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result')
            m.setID(event.getID())
            v = m.addChild(name='vCard', namespace=NS_VCARD)
            v.setTagData(tag='NICKNAME', val=yid)
            if userfile[fromstripped].has_key('avatar') and \
                userfile[fromstripped]['avatar'].has_key(yid):
                p = v.addChild(name='PHOTO')
                p.setTagData(tag='TYPE', val='image/png')
                p.setTagData(tag='BINVAL', val=base64.encodestring(userfile[fromstripped]['avatar'][yid][1]))
            self.jabberqueue(m)
        else:
            self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
        raise NodeProcessed

    def y_avatar(self,yobj,yid,avatar):
        hex = None
        conf = userfile[yobj.fromjid]
        if not conf.has_key('avatar'):
            conf['avatar']={}
        if avatar != None:
            a = sha.new(avatar)
            hex = a.hexdigest()
            conf['avatar'][yid]=(hex,avatar)
        elif conf['avatar'].has_key(yid):
            hex = ''
            del conf['avatar'][yid]
        userfile[yobj.fromjid] = conf
        userfile.sync()
        if hex != None:
            if config.dumpProtocol: print "avatar:",hex
            self.y_online(yobj,yid,forceavatar=1)

    def y_closed(self, yobj):
        if self.userlist.has_key(yobj.fromjid):
            if not yobj.connok:
                if config.dumpProtocol: print "got closed, on not connok"
                if yobj.moreservers():
                    if rdsocketlist.has_key(yobj.sock):
                        del rdsocketlist[yobj.sock]
                    if wrsocketlist.has_key(yobj.sock):
                        del wrsocketlist[yobj.sock]
                    yobj.sock.close()
                    s= yobj.connect()
                    if s != None:
                        rdsocketlist[s]=yobj
                        self.userlist[yobj.fromjid]=yobj
                        self.yahooqueue(yobj.fromjid,yobj.ymsg_send_challenge())
                        return # this method terminates here - all change please
                else:
                    self.y_loginfail(yobj)
            self.y_send_offline(yobj.fromjid)
            self.jabberqueue(Error(Presence(frm = yobj.fromjid, to = config.jid),ERR_REMOTE_SERVER_TIMEOUT))
            if yobj.pripingobj in timerlist:
                timerlist.remove(yobj.pripingobj)
            if yobj.secpingobj in timerlist:
                timerlist.remove(yobj.secpingobj)
            if 'confpingobj' in dir(yobj) and yobj.confpingobj in timerlist:
                timerlist.remove(yobj.confpingobj)
            if self.userlist.has_key(yobj.fromjid):
                del self.userlist[yobj.fromjid]
            if rdsocketlist.has_key(yobj.sock):
                del rdsocketlist[yobj.sock]
            if wrsocketlist.has_key(yobj.sock):
                del wrsocketlist[yobj.sock]
            if yobj.sock:
                yobj.sock.close()
            del yobj

    def y_ping(self, yobj):
        if config.dumpProtocol: print "got ping!"
        #freq = yobj.pripingtime*60
        freq = 5 * 60 #overide to ping time to try and reduce disconnects
        offset = int(time.time())%freq
        yobj.pripingtime = time.time()
        yobj.pripingobj=(freq,offset,self.yahooqueue,[yobj.fromjid, yobj.ymsg_send_priping()])
        timerlist.append(yobj.pripingobj)
        freq = yobj.secpingtime*60
        offset = int(time.time())%freq
        yobj.secpingtime = time.time()
        yobj.secpingobj=(freq,offset,self.yahooqueue,[yobj.fromjid, yobj.ymsg_send_secping()])
        timerlist.append(yobj.secpingobj)
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            self.jabberqueue(Presence(to = mjid, frm = config.jid))
        yobj.handlers['loginfail']= self.y_loginfail
        yobj.handlers['login']= self.y_closed
        yobj.connok = True
        self.yahooqueue(yobj.fromjid,yobj.ymsg_send_online(yobj.away, yobj.showstatus))
        if userfile[yobj.fromjid]['username'] != yobj.username:
            conf = userfile[yobj.fromjid]
            conf['username']=yobj.username
            userfile[yobj.fromjid]=conf
            self.jabberqueue(Message(to=yobj.fromjid,frm=config.jid,subject='Yahoo! login name',body='Your Yahoo! username was specified incorrectly in the configuration. This may be because of an upgrade from a previous version, the configuration has been updated'))

    def y_login(self,yobj):
        if config.dumpProtocol: print "got login"

    def y_loginfail(self,yobj, reason = None):
        if config.dumpProtocol: print "got login fail: ",reason
        if config.dumpProtocol: print yobj.conncount, yobj.moreservers()
        if yobj.moreservers() and reason == None:
            if rdsocketlist.has_key(yobj.sock):
                del rdsocketlist[yobj.sock]
            if wrsocketlist.has_key(yobj.sock):
                del wrsocketlist[yobj.sock]
            yobj.sock.close()
            s = yobj.connect()
            if s != None:
                rdsocketlist[s]=yobj
                self.userlist[yobj.fromjid]=yobj
                self.yahooqueue(yobj.fromjid,yobj.ymsg_send_challenge())
                return # this method terminates here - all change please
        else:
            # This is the no more servers or definite error case.
            if reason == 'badpassword':
                self.jabberqueue(Message(to=yobj.event.getFrom(),frm=config.jid,subject='Login Failure',body='Login Failed to Yahoo! service. The Yahoo! Service returned a bad password error Please use the registration function to check your password is correct.'))
            elif reason == 'locked':
                self.jabberqueue(Message(to=yobj.event.getFrom(),frm=config.jid,subject='Login Failure',body='Login Failed to Yahoo! service. Your account has been locked by Yahoo!.'))
            elif reason == 'imageverify':
                self.jabberqueue(Message(to=yobj.event.getFrom(),frm=config.jid,subject='Login Failure',body='Login Failed to Yahoo! service. Your account needs to be verified, unfortuantely this can not be done using the transport at this time.'))
            elif reason == 'badusername':
                if userfile[yobj.fromjid]['username'] == yobj.username:
                    # If the userdetails has a blah@foo style username try taking the domain off first, then connect again
                    if userfile[yobj.fromjid]['username'].count('@'):
                        yobj.username = yobj.username.split('@')[0]
                        if yobj.moreservers():
                            if rdsocketlist.has_key(yobj.sock):
                                del rdsocketlist[yobj.sock]
                            if wrsocketlist.has_key(yobj.sock):
                                del wrsocketlist[yobj.sock]
                            yobj.sock.close()
                            s = yobj.connect()
                            if s != None:
                                rdsocketlist[s]=yobj
                                self.userlist[yobj.fromjid]=yobj
                                self.yahooqueue(yobj.fromjid,yobj.ymsg_send_challenge())
                                self.jabberqueue(Message(to=yobj.event.getFrom(),frm=config.jid,subject='Login Failure',body='Login Failed to Yahoo! service. Please check registration details by re-registering in your client. You have an @ in your username, login will be attempted without the domain component.'))
                                return
                    else:
                        self.jabberqueue(Message(to=yobj.event.getFrom(),frm=config.jid,subject='Login Failure',body='Login Failed to Yahoo! service. Your username is not recognised by the Yahoo! service.'))
                else:
                    self.jabberqueue(Message(to=yobj.event.getFrom(),frm=config.jid,subject='Login Failure',body='Login Failed to Yahoo! service. Your username is not recognised by the Yahoo! service'))
            else:
                self.jabberqueue(Message(to=yobj.event.getFrom(),frm=config.jid,subject='Login Failure',body='Login Failed to Yahoo! service. Please check registration details by re-registering in your client'))
            self.jabberqueue(Error(yobj.event,ERR_NOT_AUTHORIZED))
            del self.userlist[yobj.fromjid]
            if rdsocketlist.has_key(yobj.sock):
                del rdsocketlist[yobj.sock]
            if wrsocketlist.has_key(yobj.sock):
                del wrsocketlist[yobj.sock]
            yobj.sock.close()
            del yobj

    def y_online(self,yobj,yid,forceavatar=0):
        hex = None
        if userfile[yobj.fromjid].has_key('avatar'):
            if config.dumpProtocol: print userfile[yobj.fromjid]['avatar'].keys(), yid
            if userfile[yobj.fromjid]['avatar'].has_key(yid):
                hex = userfile[yobj.fromjid]['avatar'][yid][0]
        if hex == None and forceavatar:
            hex = ''
        #print yobj.xresources.keys()
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            #print mjid, each
            if yobj.roster[yid][2] != None:
                status = cpformat.do(yobj.roster[yid][2])
            else:
                status = None
            if config.dumpProtocol: print status
            b = Presence(to = mjid, frm = '%s@%s/messenger'%(YIDEncode(yid), config.jid),priority = 10, show=yobj.roster[yid][1], status=status)
            if hex != None:
                b.addChild(node=Node(NODE_AVATAR,payload=[Node('hash',payload=hex)]))
                b.addChild(node=Node(NODE_VCARDUPDATE,payload=[Node('photo',payload=hex)]))
            self.jabberqueue(b)

    def y_chatonline(self,yobj, yid):
        #This is service online not person online
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            b = Presence(to = mjid, frm = '%s@%s/chat' %(YIDEncode(yid),config.jid), priority = 5)
            self.jabberqueue(b)

    def y_offline(self,yobj,yid):
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            self.jabberqueue(Presence(to=mjid, frm = '%s@%s/messenger'%(YIDEncode(yid), config.jid),typ='unavailable'))

    def y_chatoffline(self,yobj,yid):
        #This is service offline not person offline
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            self.jabberqueue(Presence(to =mjid, frm = '%s@%s/chat'%(YIDEncode(yid), config.jid),typ='unavailable'))

    def y_subscribe(self,yobj,yid,msg):
        self.jabberqueue(Presence(typ='subscribe',frm = '%s@%s' % (YIDEncode(yid), config.jid), to=yobj.fromjid,payload=unicode(cpformat.do(msg),'utf-8','replace')))

    def y_message(self,yobj,yid,msg):
        m = Message(typ='chat',frm = '%s@%s/messenger' %(YIDEncode(yid),config.jid), to=yobj.fromjid,body=unicode(cpformat.do(msg),'utf-8','replace'))
        m.setTag('x',namespace=NS_EVENT).setTag('composing')
        self.jabberqueue(m)

    def y_messagefail(self,yobj,yid,msg):
        self.jabberqueue(Error(Message(typ='chat',to = '%s@%s' %(YIDEncode(yid),config.jid), frm=yobj.fromjid,body=unicode(cpformat.do(msg))),ERR_SERVICE_UNAVAILABLE))

    def y_chatmessage(self,yobj,yid,msg):
        m = Message(typ='chat',frm = '%s@%s/chat' %(YIDEncode(yid),config.jid), to=yobj.fromjid,body=unicode(cpformat.do(msg),'utf-8','replace'))
        m.setTag('x',namespace=NS_EVENT).setTag('composing')
        self.jabberqueue(m)

    def y_roommessage(self,yobj,yid,room,msg):
        txt = unicode(cpformat.do(msg),'utf-8','replace')
        to = JID(yobj.fromjid)
        to.setResource(yobj.chatresource)
        if yobj.roomlist[room]['byyid'].has_key(yid):
            nick = yobj.roomlist[room]['byyid'][yid]['nick']
        else:
            nick = yid
        self.jabberqueue(Message(typ = 'groupchat', frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,nick),to=to,body=txt))

    def y_notify(self,yobj,yid,state):
        m = Message(typ='chat',frm = '%s@%s/messenger' %(YIDEncode(yid),config.jid), to=yobj.fromjid)
        x = m.setTag('x',namespace=NS_EVENT)
        if state:
            x.setTag('composing')
        self.jabberqueue(m)

    def y_calendar(self,yobj,url,desc):
        m = Message(frm=config.jid,to=yobj.fromjid,typ='headline', subject = "Yahoo Calendar Event", body = unicode(desc,'utf-8','replace'))
        p = m.setTag('x', namespace = 'jabber:x:oob')
        p.addChild(name = 'url',payload=url)
        self.jabberqueue(m)

    def y_email(self,yobj, fromtxt, fromaddr, subj):
        if fromtxt != None:
            bfrom = cpformat.do(fromtxt)
        else:
            bfrom = ''
        if fromaddr != None:
            bfrom = bfrom + ' <' + cpformat.do(fromaddr) + '>'
        m = Message(frm=config.jid,to=yobj.fromjid,typ='headline', subject = "Yahoo Email Event", body = 'From: %s\nSubject: %s'% (unicode(bfrom,'utf-8','replace'),unicode(cpformat.do(subj),'utf-8','replace')))
        self.jabberqueue(m)

    def y_reg_login(self,yobj):
        # registration login handler
        if config.dumpProtocol: print "got reg login"
        #m = yobj.event.buildReply('result')
        #self.jabberqueue(m)
        self.jabberqueue(Presence(to=yobj.event.getFrom(),frm=yobj.event.getTo(),typ=yobj.event.getType()))
        self.jabberqueue(Presence(typ='subscribe',to=yobj.fromjid, frm=config.jid))

    def y_reg_loginfail(self,yobj,reason = None):
        if config.dumpProtocol: print "got reg login fail: ",reason
        if yobj.moreservers() and reason != None:
            if rdsocketlist.has_key(yobj.sock):
                del rdsocketlist[yobj.sock]
            if wrsocketlist.has_key(yobj.sock):
                del wrsocketlist[yobj.sock]
            yobj.sock.close()
            s= yobj.connect()
            if s != None:
                rdsocketlist[s]=yobj
                self.userlist[yobj.fromjid]=yobj
                self.yahooqueue(yobj.fromjid,yobj.ymsg_send_challenge())
                return # this method terminates here - all change please
        # registration login failure handler
        self.jabberqueue(Error(yobj.event,ERR_NOT_ACCEPTABLE)) # will not work, no event object
        del self.userlist[yobj.fromjid]
        if rdsocketlist.has_key(yobj.sock):
            del rdsocketlist[yobj.sock]
        if wrsocketlist.has_key(yobj.sock):
            del wrsocketlist[yobj.sock]
        yobj.sock.close()
        del yobj

    def y_send_online(self,fromjid,resource=None):
        if config.dumpProtocol: print 'xmpp_online:',fromjid,self.userlist[fromjid].roster
        fromstripped = fromjid
        if resource != None:
            fromjid = JID(fromjid)
            fromjid.setResource(resource)
        self.jabberqueue(Presence(to=fromjid,frm = config.jid))
        for yid in self.userlist[fromstripped].roster:
            if self.userlist[fromstripped].roster[yid][0] == 'available':
                self.jabberqueue(Presence(frm = '%s@%s/messenger' % (YIDEncode(yid),config.jid), to = fromjid))

    def y_send_offline(self,fromjid,resource=None,status=None):
        if config.dumpProtocol: print 'xmpp_offline:',fromjid,self.userlist[fromjid].roster
        fromstripped = fromjid
        if resource != None:
            fromjid = JID(fromjid)
            fromjid.setResource(resource)
        self.jabberqueue(Presence(to=fromjid,frm = config.jid, typ='unavailable',status=status))
        if self.userlist.has_key(fromstripped):
            for yid in self.userlist[fromstripped].roster:
                if self.userlist[fromstripped].roster[yid][0] == 'available':
                    self.jabberqueue(Presence(frm = '%s@%s/messenger' % (YIDEncode(yid),config.jid), to = fromjid, typ='unavailable'))
                    self.jabberqueue(Presence(frm = '%s@%s/chat' % (YIDEncode(yid),config.jid), to = fromjid, typ='unavailable'))

    #chat room functions
    def y_chat_login(self,fromjid):
        yobj=self.userlist[fromjid]
        yobj.chatlogin=True
        if 'roomtojoin' in dir(yobj):
            self.yahooqueue(fromjid,yobj.ymsg_send_chatjoin(yobj.roomtojoin))
            del yobj.roomtojoin

    def y_chat_roominfo(self,fromjid,info):
        yobj=self.userlist[fromjid]
        if not yobj.roomlist.has_key(info['room']):
            yobj.roomlist[info['room']]={'byyid':{},'bynick':{},'info':info}
            self.jabberqueue(Presence(frm = '%s@%s' %(RoomEncode(info['room']),config.confjid),to=fromjid))
            self.jabberqueue(Message(frm = '%s@%s' %(RoomEncode(info['room']),config.confjid),to=fromjid, typ='groupchat', subject=unicode(cpformat.do(info['topic']),'utf-8','replace')))

    def y_chat_join(self,fromjid,room,info):
        yobj=self.userlist[fromjid]
        if yobj.roomlist.has_key(room):
            if not yobj.roomlist[room]['byyid'].has_key(info['yip']):
                yobj.roomlist[room]['byyid'][info['yip']] = info
                if not info.has_key('nick'):
                    info['nick'] = info['yip']
                tojid = JID(fromjid)
                tojid.setResource(yobj.chatresource)
                #print info['yip'],yobj.username
                if info['yip'] == yobj.username:
                    jid = tojid
                    if config.dumpProtocol: print info['nick'], yobj.nick
                    if info['nick'] != yobj.nick:
                        # join room with wrong nick
                        p = Presence(to = tojid, frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,yobj.nick))
                        p.addChild(node=MucUser(jid = jid, nick = yobj.nick, role = 'participant', affiliation = 'none'))
                        self.jabberqueue(p)
                        # then leave/change to the right nick
                        p = Presence(to = tojid, frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,yobj.nick), typ='unavailable')
                        p.addChild(node=MucUser(jid = jid, nick = info['nick'], role = 'participant', affiliation = 'none', status = 303))
                        self.jabberqueue(p)
                        yobj.nick = info['nick']
                else:
                    jid = '%s@%s' % (YIDEncode(info['yip']),config.jid)
                yobj.roomlist[room]['bynick'][info['nick']]= info['yip']
                self.jabberqueue(Presence(frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,info['nick']), to = tojid, payload=[MucUser(role='participant',affiliation='none',jid = jid)]))

    def y_chat_leave(self,fromjid,room,yid,nick):
        # Need to add some cleanup code
        #
        #
        yobj=self.userlist[fromjid]
        if yobj.roomlist.has_key(room):
            if yobj.roomlist[room]['byyid'].has_key(yid):
                del yobj.roomlist[room]['bynick'][yobj.roomlist[room]['byyid'][yid]['nick']]
                del yobj.roomlist[room]['byyid'][yid]
                jid = JID(fromjid)
                jid.setResource(yobj.chatresource)
                self.jabberqueue(Presence(frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,nick), to= jid, typ = 'unavailable'))

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
            yobj=self.userlist[each]
            if yobj.pripingobj in timerlist:
                timerlist.remove(yobj.pripingobj)
            if yobj.secpingobj in timerlist:
                timerlist.remove(yobj.secpingobj)
            del self.userlist[yobj.fromjid]
            if rdsocketlist.has_key(yobj.sock):
                del rdsocketlist[yobj.sock]
            if wrsocketlist.has_key(yobj.sock):
                del wrsocketlist[yobj.sock]
            yobj.sock.close()
            del yobj
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

    if config.compjid:
        xcp=1
    else:
        xcp=0
        config.compjid = config.jid

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
    connection = xmpp.client.Component(config.compjid,config.port,debug=debug,domains=[config.jid,config.confjid],sasl=sasl,bind=config.useComponentBinding,route=config.useRouteWrap,xcp=xcp)
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
                        transport.y_closed(rdsocketlist[each])
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
                        if config.dumpProtocol: ylib.printpacket(packet)
                        each.send(packet)
                    if wrsocketlist[each] == []:
                        del wrsocketlist[each]
                except socket.error:
                    transport.y_closed(rdsocketlist[each])
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
        transport.y_send_offline(each, status = transport.offlinemsg)
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
