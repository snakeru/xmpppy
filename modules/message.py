# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Kristopher Tate/BlueBridge technologies, 2005
# Help Desk implementation & Remote Administration via message stanzas

from xmpp import *
from xmppd import *
from math import *
import time

class MessageCatcher(PlugIn):
    """ Message handler for items address directly to the server. """
    NS='message'
    def plugin(self,server):
        self._data = {}
        self._owner = server
        server.Dispatcher.RegisterHandler('message',self.messageHandler,xmlns=NS_CLIENT)

    def plugout(self):
        self._owner.Dispatcher.UnregisterHandler('message',self.messageHandler)
    
    def timeDurration(self,the_time):
        days = floor(the_time/60/60/24)
        hours = floor((the_time - days*60*60*24)/60/60)
        minutes = floor((the_time - days*60*60*24 - hours*60*60)/60)
        seconds = floor((the_time - days*60*60*24 - hours*60*60 - minutes*60))
        return (days,hours,minutes,seconds)
        
    def readableTimeDurration(self,in_time):
        if type(in_time) != ((1,)): in_time = self.timeDurration(in_time)
        out = ''
        if in_time[0]>=1: out += '%i%s '%(in_time[0],'d')
        if in_time[1]>=1: out += '%i%s '%(in_time[1],'h')
        if in_time[2]>=1: out += '%i%s '%(in_time[2],'m')
        if in_time[3]>=1: out += '%i%s '%(in_time[3],'s')
        return out
            
    def messageHandler(self,session,stanza):
        try:
            body = stanza.getBody()
            split_jid = session.getSplitJID()
            bare_jid = session.getBareJID()
            if body == '1':
                out_body = 'The items below show each resource, its priority, last date of activity, and total connection time:\nNote: All times in GMT.\n\n'
                for resource in self._owner.Router._data[bare_jid].keys():
                    cr = self._owner.Router._data[bare_jid][resource]
                    s = self._owner.getsession(bare_jid+'/'+resource)
                    out_body += 're:%s pri:%s last:%s up:%s\n'%(resource,cr.getPriority(),time.strftime('%m-%d-%y %H:%M:%S',time.gmtime(s.last_seen)),self.readableTimeDurration(time.time() - s.conn_since))
        
            elif body == '2':
                out_body = ''
                data = []
                item = 1
                for resource in self._owner.Router._data[bare_jid].keys():
                    if resource != session.getResource():
                        s = self._owner.getsession(bare_jid+'/'+resource)
                        s.enqueue(Message(to=s.peer,body='Hello,\nThis location has been remotely disconnected.',frm=session.ourname))
                        data += [s]
                        out_body += '%i) %s\n'%(item,resource)
                        item += 1
                for term_session in data:
                    term_session.terminate_stream()
                
                if out_body != '':
                    out_body = 'The following resources were logged-out:\n\n' + out_body

                out_body += 'You are now logged-in from one location.'
                
            elif body == '3' or body == 'info':
                out_body = 'System status for %s:\n\n'%session.ourname
    
                data = {}
                data['soft'] = 'BlueBridge Jibber-Jabber 0.3'
                data['no_registered'] = self._owner.DB.getNumRegistered(session.ourname)
                data['uptime'] = self.readableTimeDurration(time.time() - self._owner.up_since)
                data['no_routes'] = len(self._owner.routes.keys())
                data['no_reg_users_conn'] = len(self._owner.Router._data)
                data['no_conn_servers'] = self._owner.num_servers
                data['no_msg_routed'] = self._owner.num_messages
                out_body += """    Uptime: %(uptime)s
    Software: %(soft)s
    No. Routes: %(no_routes)i
    No. Connected Servers: %(no_conn_servers)i
    No. of Registered Users: %(no_registered)i
    No. of Messages Routed: %(no_msg_routed)i
    No. Authorized Connections (1/user): %(no_reg_users_conn)i"""%data
    
            elif body == '4' or body == 'page':
                someone_online = False
                for x in self._owner.administrators[session.ourname]:
                    s = self._owner.getsession(x+'@'+session.ourname)
                    if s:
                        someone_online = True
                        s.enqueue(Message(to=x+'@'+session.ourname,body='Hey %s,\nYour friendly server here. JID <%s> has just paged you.'%(s.getName(),session.peer),frm=session.ourname))
                if someone_online == True:
                    out_body = 'A page has been sent to an administrator.\nWe cannot guarantee that it will be returned.\n\nThank-you.'
                else:
                    out_body = 'A page could not be sent to an administrator at this time. Please try back in an hour.\n\nThank-you.'
    
            elif len(body) > 1 and body.find('5') == 0 and session.isAdmin == True:
                self.DEBUG('MESSAGE HANDLER: %s'%body,'info')
                JIDS = body[2:len(body)].split(' ')
                self.DEBUG('MESSAGE HANDLER: %s'%str(JIDS),'info')
                jid_1 = self._owner.tool_split_jid(JIDS[0])
                jid_2 = self._owner.tool_split_jid(JIDS[1])
                out_body = 'Retrieving info for JID <%s> relative to JID <%s>:\n\n'%(JIDS[0],JIDS[1])
                if jid_2 == None:
                    if jid_1 == None: JIDS[0] = JIDS[0]+'@'+session.ourname
                    roster = self._owner.DB.pull_roster(session.ourname,JIDS[1],JIDS[0])                
                else:
                    roster = self._owner.DB.pull_roster(jid_2[1],jid_2[0],JIDS[0])
                if roster == None:
                    out_body += 'No data found.'
                else:
                    for x,y in roster.iteritems():
                        out_body += '%s=%s\n'%(x,y)
                
    
    
            else: 
                out_body = """Hello %s! Welcome to Help Desk.
The following menu below will give you options to choose from:
    
1. View all locations that I am currently logged in with.
2. Log-out all other locations except this one.
3. Get my system status.
4. Page an admin for later IM"""%session.getName()
            
            M=Message(to=session.peer,body=out_body,frm=session.ourname)
    #        print dir(M)
            session.enqueue(M)
        except Exception, val:
            self.DEBUG('MESSAGE HANDLER CRASHED!\n%s'%val,'error')
        raise NodeProcessed