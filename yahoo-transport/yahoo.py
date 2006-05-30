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
from curphoo import cpformat
from xmpp.protocol import *
from xmpp.browser import *
from xmpp.commands import *
from xmpp.jep0106 import *
import config, roomlist, xmlconfig, ylib
from jep0133 import *
from toolbox import *

VERSTR = 'Yahoo! Transport'
rdsocketlist = {}
wrsocketlist = {}
userlist = {}
#each item is a tuple of 4 values, 0 == frequency in seconds, 1 == offset from 0, 2 == function, 3 == arguments
timerlist = []
discoresults = {}

NODE_ADMIN='admin'
NODE_ADMIN_REGISTERED_USERS='registered-users'
NODE_ADMIN_ONLINE_USERS='online-users'
NODE_ROSTER='roster'

# colour parsing re: re.sub('\x1b\[([0-9]+)])m','<asci colour=\\1>',string)

def stripformatting(text):
    text = re.sub('\x0b','',text)
    return cpformat.do(text)
   
roomenccodere = re.compile('([^-]?)([A-Z-])')
def RoomEncode(userstr):
    return JIDEncode(roomenccodere.sub('\\1-\\2', userstr))

roomdeccodere = re.compile('-([a-zA-Z-])')
def RoomDecode(userstr):
    def decode(m):
        return m.group(1).upper()
    return roomdeccodere.sub(decode, JIDDecode(userstr))

class Connect_Registered_Users_Command(xmpp.commands.Command_Handler_Prototype):
    """This is the """
    name = "connect-users"
    description = 'Connect all registered users'
    discofeatures = [xmpp.commands.NS_COMMANDS]

    def __init__(self,jid=''):
        """Initialise the command object"""
        xmpp.commands.Command_Handler_Prototype.__init__(self,jid)
        self.initial = { 'execute':self.cmdFirstStage }

    def _DiscoHandler(self,conn,request,type):
        """The handler for discovery events"""
        if request.getFrom().getStripped() in config.admins:
            return xmpp.commands.Command_Handler_Prototype._DiscoHandler(self,conn,request,type)
        else:
            return None

    def cmdFirstStage(self,conn,request):
        """Build the reply to complete the request"""
        if request.getFrom().getStripped() in config.admins:
            for each in userfile.keys():
                conn.send(Presence(to=each, frm = config.jid, typ = 'probe'))
                if userfile[each].has_key('servers'):
                    for server in userfile[each]['servers']:
                        conn.send(Presence(to=each, frm = '%s@%s'%(server,config.jid), typ = 'probe'))
            reply = request.buildReply('result')
            form = DataForm(typ='result',data=[DataField(value='Command completed.',typ='fixed')])
            reply.addChild(name='command',attrs={'xmlns':NS_COMMAND,'node':request.getTagAttr('command','node'),'sessionid':self.getSessionID(),'status':'completed'},payload=[form])
            self._owner.send(reply)
        else:
            self._owner.send(Error(request,ERR_FORBIDDEN))
        raise NodeProcessed

class Transport:

    # This class is the main collection of where all the handlers for both the IRC and Jabber

    #Global structures
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
            s = userlist[fromjid].sock
            if not wrsocketlist.has_key(s):
                wrsocketlist[s]=[]
            wrsocketlist[s].append(packet)

    def findbadconn(self):
        #print rdsocketlist
        for each in userlist:
            print each, userlist[each].sock.fileno()
            if userlist[each].sock.fileno() == -1:
                #print each, userlist[each].sock.fileno()
                self.y_closed(userlist[each])
            else:
                try:
                    a,b,c = select.select([userlist[each].sock],[userlist[each].sock],[userlist[each].sock],0)
                except:
                    self.y_closed(userlist[each])
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
        self.jabber.RegisterHandler('iq',self.xmpp_iq_avatar, typ = 'get', ns='jabber:iq:avatar')
        self.jabber.RegisterHandler('iq',self.xmpp_iq_vcard, typ = 'get', ns=NS_VCARD)
        #self.jabber.RegisterHandler('iq',self.xmpp_iq_notimplemented)
        #self.jabber.RegisterHandler('iq',self.xmpp_iq_mucadmin_set,typ = 'set', ns=NS_MUC_ADMIN)
        #self.jabber.RegisterHandler('iq',self.xmpp_iq_mucadmin_get,typ = 'get', ns=NS_MUC_ADMIN)
        self.disco = Browser()
        self.disco.PlugIn(self.jabber)
        self.command = Commands(self.disco)
        self.command.PlugIn(self.jabber)
        self.cmdconnectusers = Connect_Registered_Users_Command(jid=config.jid)
        self.cmdconnectusers.plugin(self.command)
        self.cmdonlineusers = Online_Users_Command(userlist,jid=config.jid)
        self.cmdonlineusers.plugin(self.command)
        self.cmdactiveusers = Active_Users_Command(userlist,jid=config.jid)
        self.cmdactiveusers.plugin(self.command)
        self.cmdregisteredusers = Registered_Users_Command(userfile,jid=config.jid)
        self.cmdregisteredusers.plugin(self.command)
        self.cmdeditadminusers = Edit_Admin_List_Command(jid=config.jid)
        self.cmdeditadminusers.plugin(self.command)
        self.cmdrestartservice = Restart_Service_Command(self,jid=config.jid)
        self.cmdrestartservice.plugin(self.command)
        self.cmdshutdownservice = Shutdown_Service_Command(self,jid=config.jid)
        self.cmdshutdownservice.plugin(self.command)
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
        if event.getBody() == None:
            return
        if event.getTo().getNode() != None:
            if userlist.has_key(fromstripped):
                if event.getTo().getDomain() == config.jid:
##                    if event.getTo().getResource() == None or event.getTo().getResource() == '':
##                        #print "no resource", userlist[fromstripped].resources
##                        if userlist[fromstripped].resources.has_key(event.getTo().getNode()):
##                            if 'messenger' in userlist[fromstripped].resources[event.getTo().getNode()]:
##                                resource= 'messenger'
##                            elif 'chat' in userlist[fromstripped].resources[event.getTo().getNode()]:
##                                resource = 'chat'
##                    elif event.getTo().getResource() == 'chat':
##                        resource = 'chat'
##                    elif event.getTo().getResource() == 'messenger':
##                        resource = 'messenger'
##                    else:
##                        resource = 'messenger'
                    resource = 'messenger'
                        # normal non-groupchat or conference cases
                    if resource == 'messenger':
                        if event.getType() == None or event.getType() =='normal':
                            # normal message case
                            #print 'got message'
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_message(event.getTo().getNode().encode('utf-8'),event.getBody().encode('utf-8')))
                        elif event.getType() == 'chat':
                            # normal chat case
                            #print 'got message'
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_message(event.getTo().getNode().encode('utf-8'),event.getBody().encode('utf-8')))
                        else:
                            #print 'type error'
                            self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                    elif resource == 'chat':
                        if event.getType() == None or event.getType() =='normal':
                            # normal message case
                            #print 'got message'
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_chatmessage(event.getTo().getNode().encode('utf-8'),event.getBody().encode('utf-8')))
                        elif event.getType() == 'chat':
                            # normal chat case
                            #print 'got message'
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_chatmessage(event.getTo().getNode().encode('utf-8'),event.getBody().encode('utf-8')))
                        else:
                            #print 'type error'
                            self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                    else:
                        #print 'resource error'
                        self.jabberqueue(Error(event,ERR_BAD_REQUEST))
                elif event.getTo().getDomain() == config.confjid:
                    # Must add resource matching here, ie only connected resource can send to room.
                    if event.getSubject():
                        self.jabberqueue(Error(event,ERR_NOT_IMPLEMENTED))
                        return
                    if event.getTo().getResource() == None or event.getTo().getResource() == '':
                        print userlist[fromstripped].roomlist, userlist[fromstripped].roomnames
                        if userlist[fromstripped].roomlist.has_key(RoomDecode(event.getTo().getNode().encode('utf-8'))):
                            room = RoomDecode(event.getTo().getNode().encode('utf-8'))
                        elif userlist[fromstripped].roomnames.has_key(event.getTo().getNode()):
                            room = userlist[fromstripped].roomnames[event.getTo().getNode()].encode('utf-8')
                        else:
                            room = None
                        print "groupchat room: ",room
                        if room != None:
                            if event.getBody()[0:3] == '/me':
                                type = 2
                                body = event.getBody()[4:].encode('utf-8')
                            else:
                                type = 1
                                body = event.getBody().encode('utf-8')
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_roommsg(room,body,type))
                            to = '%s/%s'%(event.getTo(),userlist[fromstripped].username)
                            self.jabberqueue(Message(to=event.getFrom(), frm= to, typ='groupchat',body=event.getBody()))
                        else:
                            self.jabberqueue(Error(event,ERR_BAD_REQUEST))
            else:
                print 'no item error'
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
                if event.getType() == 'subscribed':
                    if userlist.has_key(fromstripped):
                        if event.getTo() == config.jid:
                            conf = userfile[fromstripped]
                            conf['subscribed']=True
                            userfile[fromstripped]=conf
                            userfile.sync()
                            #For each new user check if rosterx is adversited then do the rosterx message, else send a truckload of subscribes.
                            #Part 1, parse the features out of the disco result
                            features = []
                            if discoresults.has_key(event.getFrom().getStripped().encode('utf8')):
                                discoresult = discoresults[event.getFrom().getStripped().encode('utf8')]
                                #for i in discoresult.getQueryPayload():
                                if discoresult.getTag('query').getTag('feature'): features.append(discoresult.getTag('query').getAttr('var'))
                            #Part 2, make the rosterX message
                            if NS_ROSTERX in features:
                                m = Message(to = fromjid, frm = config.jid, subject= 'Yahoo Roster Items', body = 'Items from Yahoo Roster')
                                p=None
                                p= m.setTag('x',namespace = NS_ROSTERX)
                                yrost = userlist[fromstripped].buddylist
                                print yrost
                                for each in yrost.keys():
                                    for i in yrost[each]:
                                        p.addChild(name='item', attrs={'jid':'%s@%s'%(i,config.jid),'name':i, 'action':'add'},payload=[Node('group',payload=each)])
                                self.jabberqueue(m)
                                print m
                            else:
                                for each in userlist[fromstripped].buddylist.keys():
                                    for i in userlist[fromstripped].buddylist[each]:
                                        self.jabberqueue(Presence(frm='%s@%s'%(i,config.jid),to = fromjid, typ='subscribe', status='Yahoo messenger contact'))
                            m = Presence(to = fromjid, frm = config.jid)
                            self.jabberqueue(m)
                            self.y_send_online(fromstripped)
                            self.register_ymsg_handlers(userlist[fromstripped])
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'subscribe':
                    if userlist.has_key(fromstripped):
                        if event.getTo() == config.jid:
                            conf = userfile[fromstripped]
                            conf['usubscribed']=True
                            userfile[fromstripped]=conf
                            userfile.sync()
                            m = Presence(to = fromjid, frm = config.jid, typ = 'subscribed')
                            self.jabberqueue(m)
                        elif userlist[fromstripped].roster.has_key(event.getTo().getNode().encode('utf-8')):
                            m = Presence(to = fromjid, frm = event.getTo(), typ = 'subscribed')
                            self.jabberqueue(m)
                        else:
                            #add new user case.
                            if event.getStatus() != None:
                                print event.getStatus().encode('utf-8')
                                status = event.getStatus().encode('utf-8')
                            else:
                                status = ''
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_addbuddy(event.getTo().getNode().encode('utf-8'), status))
                            self.jabberqueue(Presence(frm=event.getTo(), to = event.getFrom(), typ = 'subscribed'))
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'unsubscribe':
                    if userlist.has_key(fromstripped):
                        if userlist[fromstripped].roster.has_key(event.getTo().getNode()):
                            if event.getStatus() != None:
                                msg = event.getStatus().encode('utf-8')
                            else:
                                msg = ''
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_delbuddy(event.getTo().getNode().encode('utf-8'), msg))
                            self.jabberqueue(Presence(frm=event.getTo(), to = event.getFrom(), typ = 'unsubscribed'))
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                elif event.getType() == 'unsubscribed':
                    # should do something more elegant here
                    pass
                elif event.getType() == None or event.getType() == 'available' or event.getType() == 'invisible':
                    # code to add yahoo connection goes here
                    if event.getTo().getNode() != '':
                        return
                    if userlist.has_key(fromstripped):
                        # update status case and additional resource case
                        # update status case
                        if userlist[fromstripped].xresources.has_key(event.getFrom().getResource()):
                            #update resource record
                            userlist[fromstripped].xresources[event.getFrom().getResource()]=(event.getShow(),event.getPriority(),event.getStatus(),userlist[fromstripped].xresources[event.getFrom().getResource()][3])
                            print "Update resource login: %s" % userlist[fromstripped].xresources
                        else:
                            #new resource login
                            userlist[fromstripped].xresources[event.getFrom().getResource()]=(event.getShow(),event.getPriority(),event.getStatus(),time.time())
                            print "New resource login: %s" % userlist[fromstripped].xresources
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
                        yobj = ylib.YahooCon(conf['username'].encode('utf-8'),conf['password'].encode('utf-8'), fromstripped,config.host)
                        #userlist[fromstripped]=yobj
                        s = yobj.connect()
                        if s != None:
                            rdsocketlist[s]=yobj
                            userlist[yobj.fromjid]=yobj
                            self.register_ymsg_handlers(userlist[fromstripped])
                            #self.yahooqueue(fromstripped,yobj.ymsg_send_challenge())
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
                    if userlist.has_key(fromstripped):
                        #print 'Resource: ', event.getFrom().getResource(), "To Node: ",event.getTo().getNode()
                        if event.getTo().getNode() =='':
                            self.y_send_offline(fromstripped,event.getFrom().getResource())
                            if userlist[fromstripped].xresources.has_key(event.getFrom().getResource()):
                                del userlist[fromstripped].xresources[event.getFrom().getResource()]
                                self.xmpp_presence_do_update(event,fromstripped)
                            #Single resource case
                            #print userlist[fromstripped].xresources
                            if userlist[fromstripped].xresources == {}:
                                print 'No more resource logins'
                                yobj=userlist[fromstripped]
                                if yobj.pripingobj in timerlist:
                                    timerlist.remove(yobj.pripingobj)
                                if yobj.secpingobj in timerlist:
                                    timerlist.remove(yobj.secpingobj)
                                del userlist[yobj.fromjid]
                                del rdsocketlist[yobj.sock]
                                yobj.sock.close()
                                del yobj
                    else:
                        self.jabberqueue(Presence(to=fromjid,frm = config.jid, typ='unavailable'))
            elif event.getTo().getDomain() == config.confjid:
                #Need to move Chatpings into this section for Yahoo rooms.
                if userlist.has_key(fromstripped):
                    if userlist[fromstripped].connok:
                        print "chat presence"
                        try:
                            #print event.getTo().getNode().encode('utf-8').decode('base64')
                            room = unicode(RoomDecode(event.getTo().getNode().encode('utf-8')),'utf-8','strict')
                        except:
                            if userlist[fromstripped].roomnames.has_key(event.getTo().getNode()):
                                room = userlist[fromstripped].roomnames[event.getTo().getNode()]
                            else:
                                self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                                print "decode error"
                                return
                        userlist[fromstripped].roomnames[event.getTo().getNode().lower()] = room
                        if event.getType() == 'available' or event.getType() == None or event.getType() == '':
                            nick = event.getTo().getResource()
                            userlist[fromstripped].nick = nick
                            if not userlist[fromstripped].chatlogin:
                                self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_conflogon())
                                self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_chatlogin(None))
                                userlist[fromstripped].chatresource = event.getFrom().getResource()
                                #Add secondary ping object code
                                freq = 5 * 60 #Secondary ping frequency from Zinc
                                offset = int(time.time())%freq
                                userlist[fromstripped].confpingtime = time.time()
                                userlist[fromstripped].confpingobj=(freq,offset,self.yahooqueue,[userlist[fromstripped].fromjid, userlist[fromstripped].ymsg_send_confping()])
                                timerlist.append(userlist[fromstripped].confpingobj)
                                userlist[fromstripped].roomtojoin = room.encode('utf-8')
                            else:
                                self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_chatjoin(room.encode('utf-8')))
                        elif event.getType() == 'unavailable':
                            # Must add code to compare from resources here
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_chatleave(room.encode('utf-8')))
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_chatlogout())
                            self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_conflogoff())
                            if userlist[fromstripped].confpingobj in timerlist:
                                timerlist.remove(userlist[fromstripped].confpingobj)
                        else:
                            self.jabberqueue(Error(event,ERR_FEATURE_NOT_IMPLEMENTED))
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
        for each in userlist[fromstripped].xresources.keys():
            #print each,userlist[fromstripped].xresources
            if userlist[fromstripped].xresources[each][1]>priority:
                #if priority is higher then take the highest
                age = userlist[fromstripped].xresources[each][3]
                priority = userlist[fromstripped].xresources[each][1]
                resource = each
            elif userlist[fromstripped].xresources[each][1]==priority:
                #if priority is the same then take the oldest
                if userlist[fromstripped].xresources[each][3]<age:
                    age = userlist[fromstripped].xresources[each][3]
                    priority = userlist[fromstripped].xresources[each][1]
                    resource = each
        if resource == event.getFrom().getResource():
            #only update shown status if resource is current datasource
            if event.getShow() == None:
                if event.getStatus() != None:
                    self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_away(None,event.getStatus()))
                elif userlist[fromstripped].away == None:
                    self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_back())
            elif event.getShow() == None and userlist[fromstripped].away != None:
                self.yahooqueue(fromstripped,userlist[fromstripped].ymsg_send_away(None,event.getStatus()))
                userlist[fromstripped].away = None
            elif event.getShow() == 'xa' or event.getShow() == 'away':
                self.yahooqueue(fromstripped, userlist[fromstripped].ymsg_send_away('away',event.getStatus()))
                userlist[fromstripped].away = 'away'
            elif event.getShow() == 'dnd':
                self.yahooqueue(fromstripped, userlist[fromstripped].ymsg_send_away('dnd',event.getStatus()))
                userlist[fromstripped].away= 'dnd'
            elif event.getType() == 'invisible':
                self.yahooqueue(fromstripped, userlist[fromstripped].ymsg_send_away('invisible',None))
                userlist[fromstripped].away= 'invisible'

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
                    return {
                        'ids':[
                            {'category':'gateway','type':'yahoo','name':VERSTR}],
                        'features':[NS_REGISTER,NS_VERSION,NS_COMMANDS]}
                if type == 'items':
                    list = [
                        {'node':NODE_ROSTER,'name':VERSTR + ' Roster','jid':config.jid},
                        {'jid':config.confjid,'name':VERSTR + ' Chatrooms'}]
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
                    if userlist.has_key(fromstripped):
                        for each in userlist[fromstripped].roster.keys():
                            list.append({'jid':'%s@%s' %(each,config.jid),'name':each})
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
                            list.append({'node':'/'.join([NODE_ADMIN_REGISTERED_USERS, each]),'name':each,'jid':config.jid})
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
                        for each in userlist.keys():
                            list.append({'node':'/'.join([NODE_ADMIN_ONLINE_USERS, each]),'name':each,'jid':config.jid})
                    return list
            else:
                self.jabber.send(Error(event,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
        elif to.getDomain() == config.jid:
            if userlist.has_key(fromstripped):
                if type == 'info':
                    if userlist[fromstripped].roster.has_key(to.getNode()):
                        features = []
                        if userfile[fromstripped.encode('utf-8')].has_key('avatar'):
                            if userfile[fromstripped.encode('utf-8')]['avatar'].has_key(to.getNode()):
                                features.append({'var':'jabber:iq:avatar'})
                        return {
                            'ids':[
                                {'category':'client','type':'yahoo','name':to.getNode()}],
                            'features':features}
                    else:
                        self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
                if type == 'items':
                    if userlist[fromstripped].roster.has_key(to.getNode()):
                        return []
            else:
                self.jabberqueue(Error(event,ERR_NOT_ACCEPTABLE))
        elif to == config.confjid:
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
        elif to.getDomain() == config.confjid:
            if type == 'info':
                str = unicode(RoomDecode(to.getNode().encode('utf-8')),'utf-8','strict')
                lobby,room = str.split(':')
                result = {
                    'ids':[
                        {'category':'conference','type':'yahoo','name':str}],
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
        discoresults[event.getFrom().getStripped().encode('utf8')]=event
        raise NodeProcessed

    def xmpp_iq_register_get(self, con, event):
        if event.getTo() == config.jid:
            username = []
            password = []
            fromjid = event.getFrom().getStripped().encode('utf8')
            if userfile.has_key(fromjid):
                try:
                    username = userfile[fromjid]['username']
                    password = userfile[fromjid]['password']
                except:
                    pass
            m = event.buildReply('result')
            m.setQueryNS(NS_REGISTER)
            m.setQueryPayload([Node('instructions', payload = 'Please provide your Yahoo! username and password'),Node('username',payload=username),Node('password',payload=password),Node('registered')])
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
                    conf = {}
                conf['username']=username
                conf['password']=password
                userfile[fromjid]=conf
                userfile.sync()
                m=event.buildReply('result')
                self.jabberqueue(m)
                if userlist.has_key(fromjid):
                    self.y_closed(userlist[fromjid])
                if not userlist.has_key(fromjid):
                    yobj = ylib.YahooCon(username.encode('utf-8'),password.encode('utf-8'), fromjid,config.host)
                    userlist[fromjid]=yobj
                    print "try connect"
                    s = yobj.connect()
                    if s != None:
                        print "conect made"
                        rdsocketlist[s]=yobj
                        userlist[fromjid]=yobj
                        self.yahooqueue(fromjid,yobj.ymsg_send_challenge())
                    yobj.handlers['login']=self.y_reg_login
                    yobj.handlers['loginfail']=self.y_reg_loginfail
                    yobj.handlers['closed']=self.y_reg_loginfail
                    yobj.handlers['ping']=self.y_ping
                    yobj.event = event
                    yobj.showstatus = None
                    yobj.away = None
            elif remove and not username and not password:
                if userlist.has_key(fromjid):
                    self.y_closed(userlist[fromjid])
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
            if userfile[fromstripped].has_key('avatar'):
                if userfile[fromstripped]['avatar'].has_key(event.getTo().getNode()):
                    m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result', queryNS='jabber:iq:avatar', payload=[Node('data',attrs={'mimetype':'image/png'},payload=base64.encodestring(userfile[fromstripped]['avatar'][event.getTo().getNode()][1]))])
                    m.setID(event.getID())
                    self.jabberqueue(m)
                else:
                    self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
            else:
                self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
        else:
            self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
        raise NodeProcessed

    def xmpp_iq_vcard(self, con, event):
        fromjid = event.getFrom()
        fromstripped = fromjid.getStripped().encode('utf-8')
        if userfile.has_key(fromstripped):
            if userfile[fromstripped].has_key('avatar'):
                if userfile[fromstripped]['avatar'].has_key(event.getTo().getNode()):
                    m = Iq(to = event.getFrom(), frm=event.getTo(), typ = 'result')
                    m.setID(event.getID())
                    v = m.addChild(name='vCard', namespace=NS_VCARD)
                    p = v.addChild(name='PHOTO')
                    p.setTagData(tag='TYPE', val='image/png')
                    p.setTagData(tag='BINVAL', val=base64.encodestring(userfile[fromstripped]['avatar'][event.getTo().getNode()][1]))
                    self.jabberqueue(m)
                else:
                    self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
            else:
                self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
        else:
            self.jabberqueue(Error(event,ERR_ITEM_NOT_FOUND))
        raise NodeProcessed

    def y_avatar(self,fromjid,yid,avatar):
        if avatar != None:
            a = sha.new(avatar)
            hex = a.hexdigest()
        conf = userfile[fromjid]
        if not conf.has_key('avatar'):
            conf['avatar']={}
        conf['avatar'][yid]=(hex,avatar)
        userfile[fromjid] = conf
        userfile.sync()

    def y_closed(self, yobj):
        if userlist.has_key(yobj.fromjid):
            if not yobj.connok:
                if yobj.moreservers():
                    del rdsocketlist[yobj.sock]
                    if wrsocketlist.has_key(yobj.sock):
                        del wrsocketlist[yobj.sock]
                    yobj.sock.close()
                    s= yobj.connect()
                    if s != None:
                        rdsocketlist[s]=yobj
                        userlist[yobj.fromjid]=yobj
                        self.yahooqueue(yobj.fromjid,yobj.ymsg_send_challenge())
                        return # this method terminates here - all change please
                else:
                    self.y_loginfail(yobj)
            self.jabberqueue(Presence(to = yobj.fromjid, frm = config.jid, typ='unavailable'))
            self.jabberqueue(Error(Presence(frm = yobj.fromjid, to = config.jid),ERR_REMOTE_SERVER_TIMEOUT))
            if yobj.pripingobj in timerlist:
                timerlist.remove(yobj.pripingobj)
            if yobj.secpingobj in timerlist:
                timerlist.remove(yobj.secpingobj)
            try:
                if yobj.confpingobj in timerlist:
                    timerlist.remove(yobj.confpingobj)
            except AttributeError:
                pass
            if userlist.has_key(yobj.fromjid):
                del userlist[yobj.fromjid]
            if rdsocketlist.has_key(yobj.sock):
                del rdsocketlist[yobj.sock]
            if wrsocketlist.has_key(yobj.sock):
                del wrsocketlist[yobj.sock]
            #yobj.sock.close()
            del yobj

    def y_ping(self, yobj):
        print "got ping!"
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
        print "got login"

    def y_loginfail(self,yobj, reason = None):
        print "got login fail: ",reason
        print yobj.conncount, yobj.moreservers()
        if yobj.moreservers() and reason == None:
            del rdsocketlist[yobj.sock]
            yobj.sock.close()
            s = yobj.connect()
            if s != None:
                rdsocketlist[s]=yobj
                userlist[yobj.fromjid]=yobj
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
                        yobj.username == yobj.username.split('@')[0]
                        if yobj.moreservers():
                            del rdsocketlist[yobj.sock]
                            yobj.sock.close()
                            s = yobj.connect()
                            if s != None:
                                rdsocketlist[s]=yobj
                                userlist[yobj.fromjid]=yobj
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
            del userlist[yobj.fromjid]
            del rdsocketlist[yobj.sock]
            yobj.sock.close()
            del yobj

    def y_online(self,yobj,name):
        #print yobj.xresources.keys()
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            #print mjid, each
            if yobj.roster[name][2] != None:
                status = stripformatting(yobj.roster[name][2])
            else:
                status = None
            print status
            b = Presence(to = mjid, frm = '%s@%s/messenger'%(name, config.jid),priority = 10, show=yobj.roster[name][1], status=status)
            if userfile[yobj.fromjid].has_key('avatar'):
                print userfile[yobj.fromjid]['avatar'].keys(), name
                if userfile[yobj.fromjid]['avatar'].has_key(name):
                    b.addChild(node=Node('x',attrs={'xmlns':'jabber:x:avatar'},payload=[Node('hash',payload=userfile[yobj.fromjid]['avatar'][name][0])]))
            self.jabberqueue(b)

    def y_chatonline(self,yobj, name):
        #This is service online not person online
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            b = Presence(to = mjid, frm = '%s@%s/chat' %(name,config.jid), priority = 5)
            self.jabberqueue(b)

    def y_offline(self,yobj,name):
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            self.jabberqueue(Presence(to=mjid, frm = '%s@%s/messenger'%(name, config.jid),typ='unavailable'))

    def y_chatoffline(self,yobj,name):
        #This is service offline not person offline
        for each in yobj.xresources.keys():
            mjid = JID(yobj.fromjid)
            mjid.setResource(each)
            self.jabberqueue(Presence(to =mjid, frm = '%s@%s/chat'%(name, config.jid),typ='unavailable'))

    def y_subscribe(self,yobj,nick,msg):
        self.jabberqueue(Presence(typ='subscribe',frm = '%s@%s' % (nick, config.jid), to=yobj.fromjid,payload=msg))

    def y_message(self,yobj,nick,msg):
        self.jabberqueue(Message(typ='chat',frm = '%s@%s/messenger' %(nick,config.jid), to=yobj.fromjid,body=stripformatting(msg)))

    def y_messagefail(self,yobj,nick,msg):
        self.jabberqueue(Error(Message(typ='chat',to = '%s@%s' %(nick,config.jid), frm=yobj.fromjid,body=msg),ERR_SERVICE_UNAVAILABLE))

    def y_chatmessage(self,yobj,nick,msg):
        self.jabberqueue(Message(typ='chat',frm = '%s@%s/chat' %(nick,config.jid), to=yobj.fromjid,body=stripformatting(msg)))

    def y_roommessage(self,yobj,yid,room,msg):
        txt = stripformatting(msg)
        to = JID(yobj.fromjid)
        to.setResource(yobj.chatresource)
        if yobj.roomlist[room]['byyid'].has_key(yid):
            nick = yobj.roomlist[room]['byyid'][yid]['nick']
        else:
            nick = yid
        self.jabberqueue(Message(typ = 'groupchat', frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,nick),to=to,body=txt))

    def y_calendar(self,yobj,url,desc):
        m = Message(frm=config.jid,to=yobj.fromjid,typ='headline', subject = "Yahoo Calendar Event", body = desc)
        p = m.setTag('x', namespace = 'jabber:x:oob')
        p.addChild(name = 'url',payload=url)
        self.jabberqueue(m)

    def y_email(self,yobj, fromtxt, fromaddr, subj):
        if fromtxt != None:
            bfrom = stripformatting(fromtxt)
        else:
            bfrom = ''
        if fromaddr != None:
            bfrom = bfrom + ' <' + stripformatting(fromaddr) + '>'
        m = Message(frm=config.jid,to=yobj.fromjid,typ='headline', subject = "Yahoo Email Event", body = 'From: %s\nSubject: %s'% (unicode(bfrom,'utf-8','replace'),unicode(stripformatting(subj),'utf-8','replace')))
        self.jabberqueue(m)

    def y_reg_login(self,yobj):
        # registration login handler
        print "got reg login"
        #m = yobj.event.buildReply('result')
        #self.jabberqueue(m)
        self.jabberqueue(Presence(to=yobj.event.getFrom(),frm=yobj.event.getTo(),typ=yobj.event.getType()))
        self.jabberqueue(Presence(typ='subscribe',to=yobj.fromjid, frm=config.jid))

    def y_reg_loginfail(self,yobj,reason = None):
        print "got reg login fail"
        if yobj.moreservers() and reason != None:
            del rdsocketlist[yobj.sock]
            yobj.sock.close()
            s= yobj.connect()
            if s != None:
                rdsocketlist[s]=yobj
                userlist[yobj.fromjid]=yobj
                self.yahooqueue(yobj.fromjid,yobj.ymsg_send_challenge())
                return # this method terminates here - all change please
        # registration login failure handler
        self.jabberqueue(Error(yobj.event,ERR_NOT_ACCEPTABLE)) # will not work, no event object
        del userlist[yobj.fromjid]
        del rdsocketlist[yobj.sock]
        yobj.sock.close()
        del yobj

    def y_send_online(self,fromjid,resource=None):
        print fromjid,userlist[fromjid].roster
        fromstripped = fromjid
        if resource != None:
            fromjid = JID(fromjid)
            fromjid.setResource(resource)
        self.jabberqueue(Presence(to=fromjid,frm = config.jid))
        for each in userlist[fromstripped].roster:
            if userlist[fromstripped].roster[each][0] == 'available':
                self.jabberqueue(Presence(frm = '%s@%s/messenger' % (each,config.jid), to = fromjid))

    def y_send_offline(self,fromjid,resource=None):
        print fromjid,userlist[fromjid].roster
        fromstripped = fromjid
        if resource != None:
            fromjid = JID(fromjid)
            fromjid.setResource(resource)
        self.jabberqueue(Presence(to=fromjid,frm = config.jid, typ='unavailable'))
        for each in userlist[fromstripped].roster:
            if userlist[fromstripped].roster[each][0] == 'available':
                self.jabberqueue(Presence(frm = '%s@%s/messenger' % (each,config.jid), to = fromjid, typ='unavailable'))
                self.jabberqueue(Presence(frm = '%s@%s/chat' % (each,config.jid), to = fromjid, typ='unavailable'))

    #chat room functions
    def y_chat_login(self,fromjid):
        userlist[fromjid].chatlogin=True
        self.yahooqueue(fromjid,userlist[fromjid].ymsg_send_chatjoin(userlist[fromjid].roomtojoin))
        del userlist[fromjid].roomtojoin

    def y_chat_roominfo(self,fromjid,info):
        if not userlist[fromjid].roomlist.has_key(info['room']):
            userlist[fromjid].roomlist[info['room']]={'byyid':{},'bynick':{},'info':info}
            self.jabberqueue(Presence(frm = '%s@%s' %(RoomEncode(info['room']),config.confjid),to=fromjid))
            self.jabberqueue(Message(frm = '%s@%s' %(RoomEncode(info['room']),config.confjid),to=fromjid, typ='groupchat', subject= info['topic']))

    def y_chat_join(self,fromjid,room,info):
        if userlist[fromjid].roomlist.has_key(room):
            if not userlist[fromjid].roomlist[room]['byyid'].has_key(info['yip']):
                userlist[fromjid].roomlist[room]['byyid'][info['yip']] = info
                if not info.has_key('nick'):
                    info['nick'] = info['yip']
                tojid = JID(fromjid)
                tojid.setResource(userlist[fromjid].chatresource)
                #print info['yip'],userlist[fromjid].username
                if info['yip'] == userlist[fromjid].username:
                    jid = tojid
                    print info['nick'], userlist[fromjid].nick
                    if info['nick'] != userlist[fromjid].nick:
                        # join room with wrong nick
                        p = Presence(to = tojid, frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,userlist[fromjid].nick))
                        p.addChild(node=MucUser(jid = jid, nick = userlist[fromjid].nick, role = 'participant', affiliation = 'none'))
                        self.jabberqueue(p)
                        # then leave/change to the right nick
                        p = Presence(to = tojid, frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,userlist[fromjid].nick), typ='unavailable')
                        p.addChild(node=MucUser(jid = jid, nick = info['nick'], role = 'participant', affiliation = 'none', status = 303))
                        self.jabberqueue(p)
                        userlist[fromjid].nick = info['nick']
                else:
                    jid = '%s@%s' % (info['yip'],config.jid)
                userlist[fromjid].roomlist[room]['bynick'][info['nick']]= info['yip']
                self.jabberqueue(Presence(frm = '%s@%s/%s' % (RoomEncode(room),config.confjid,info['nick']), to = tojid, payload=[MucUser(role='participant',affiliation='none',jid = jid)]))

    def y_chat_leave(self,fromjid,room,yid,nick):
        # Need to add some cleanup code
        #
        #
        if userlist[fromjid].roomlist.has_key(room):
            if userlist[fromjid].roomlist[room]['byyid'].has_key(yid):
                del userlist[fromjid].roomlist[room]['bynick'][userlist[fromjid].roomlist[room]['byyid'][yid]['nick']]
                del userlist[fromjid].roomlist[room]['byyid'][yid]
                jid = JID(fromjid)
                jid.setResource(userlist[fromjid].chatresource)
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
        if connected:
            self.register_handlers()
            #print "try auth"
            connected = self.jabber.auth(config.saslUsername,config.secret)
            #print "auth return",connected
        return connected

    def xmpp_disconnect(self):
        for each in userlist.keys():
        #    for item in self.users[each].keys():
        #        self.irc_doquit(self.users[each][item])
            del userlist[each]
        del rdsocketlist[self.jabber.Connection._sock]
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
    print "Configuration file not found. You need to create a config file and put it in one of these locations:\n    " + "\n    ".join(configFiles)
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
    #trans.offlinemsg = 'Signal handler called with signal %s'%signum
    trans.online = 0

if __name__ == '__main__':
    if 'PID' in os.environ:
        config.pid = os.environ['PID']
    loadConfig()
    if config.pid:
        pidfile = open(config.pid,'w')
        pidfile.write(`os.getpid()`)
        pidfile.close()

    if config.saslUsername:
        component = 1
    else:
        config.saslUsername = config.jid
        component = 0

    userfile = shelve.open(config.spoolFile)
    logfile = None
    if config.debugFile:
        logfile = open(config.debugFile,'a')

    connection = xmpp.client.Component(config.jid,config.port,component=component,domains=[config.jid,config.confjid])
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
        except ValueError:
            print "Value Error", rdsocketlist, wrsocketlist
            transport.findbadconn()
        except socket.error:
            print "Bad Socket", rdsocketlist, wrsocketlist
            transport.findbadconn()
        for each in i:
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
            try:
                if rdsocketlist[each] == 'xmpp':
                    while select.select([],[each],[])[1] and wrsocketlist[each] != []:
                        connection.send(wrsocketlist[each].pop(0))
                else:
                    #print wrsocketlist
                    each.send(wrsocketlist[each].pop(0))
                if wrsocketlist[each] == []:
                    del wrsocketlist[each]
            except KeyError:
                pass
            except socket.error:
                transport.y_closed(rdsocketlist[each])
            except:
                logError()
        #delayed execution method modified from python-irclib written by Joel Rosdahl <joel@rosdahl.net>
        for each in timerlist:
            #print int(time.time())%each[0]-each[1]
            if not (int(time.time())%each[0]-each[1]):
                try:
                    apply(each[2],each[3])
                except:
                    logError()
    for each in [x for x in userlist.keys()]:
        userlist[each].connok = False
        transport.y_closed(userlist[each])
        connection.send(Presence(to=each, frm = config.jid, typ = 'unavailable', status = transport.offlinemsg))
        del userlist[each]
    del rdsocketlist[connection.Connection._sock]
    userfile.close()
    connection.disconnect()
    if config.pid:
        os.unlink(config.pid)
    if logfile:
        logfile.close()
    if transport.restart:
        args=[sys.executable]+sys.argv
        if os.name == 'nt':
            def quote(a): return "\"%s\"" % a
            args = map(quote, args)
        #print sys.executable, args
        os.execv(sys.executable, args)
