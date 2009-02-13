#! /usr/bin/env python

# MXit driver test script.
from mxit_helpers import *
import socket, time, traceback
import re
import random


def printpacket(packet):
    s,u = mxit_dehdr(packet)
    t = mxit_deargu(u[:s[2]])
    print 'send', s, t, len(packet)


# MXit Functions
class MXitCon:
    rbuf = ''
    pripingobj = None
    secpingobj = None
    confpingojb = None
    session = ''
    host = 'stream.mxit.co.za'
    hostlist = socket.gethostbyname_ex(host)[2]
    port = 9119
    sock = None
    # a dictionary of groups and members
    buddylist = {}
    # Tuple by availabilaity, show value, status message
    roster = {}
    handlers = {}
    # login -- on sucessful login
    # loginfail -- on login failure

    def __init__(self, username, password, clientid, fromjid,fromhost,dumpProtocol):
        self.username = username
        self.session = username
        self.password = password
        self.clientkey = clientid[2:int(clientid[:2],16)+2]
        self.fromhost = fromhost
        self.fromjid = fromjid
        self.roster = {}
        self.buddylist = {}
        self.away = False
        #variables for public MUC
        self.alias = username
        #Each room has a list of participants in the form of {username:(alias,state,statemsg)}
        self.roomlist = {}
        self.roomnames = {} #Dictionary entry for *NAUGHTY* clients that lowercase the JID
        self.chatlogin = False
        self.chatresource = None
        #login junk
        self.connok = False
        self.conncount = 0
        self.cookies = []
        self.resources = {}
        self.xresources = {}
        self.offset = int(random.random()*len(self.hostlist))
        self.dumpProtocol = dumpProtocol

    # utility methods
    def connect(self):
        self.connok=False
        if self.dumpProtocol: print "conncount", self.conncount, self.hostlist
        while self.conncount != len(self.hostlist):
            self.sock = None
            self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.sock.bind((self.fromhost,0))
            try:
                if not self.sock.connect((self.hostlist[(self.offset+self.conncount)%len(self.hostlist)],self.port)):
                    self.conncount = self.conncount + 1
                    return self.sock
            except socket.error:
                self.conncount = self.conncount + 1
                pass
        return None

    def moreservers(self):
        if self.conncount < len(self.hostlist):
            if self.dumpProtocol: print "more servers %s %s" % (len(self.hostlist),self.conncount)
            return True
        else:
            return False

    def mxit_parsebuddies(self,list):
        #if self.dumpProtocol: print "Before: ",self.roster
        for each in list:
            if self.dumpProtocol: print 'buddy',repr(each)
            if type(each) == type([]):
                if len(each) == 5:
                    [group, jid, nick, hidenumber, xport] = each
                    if not self.buddylist.has_key(group):
                        self.buddylist[group] = []
                    self.buddylist[group].append((jid,nick))
                    if not self.roster.has_key(jid):
                        self.roster[jid]=('unavailable',None, None)
                elif len(each) == 4:
                    pass #invite
        #if self.dumpProtocol: print "After: ", self.roster

    # decoding handlers
    def mxit_login(self,hdr,pay):
        # process login packet
        if self.dumpProtocol: print 'login',pay[1]
        if pay[1] == '0':
            self.mxit_parsebuddies(pay[5:-1])
            # need to process offline messages too (comes through as the last item)
            #if self.dumpProtocol: print "got to login handler"
            if self.handlers.has_key('login'):
                self.handlers['login'](self)
        elif len(pay[1]) > 1 and pay[1][0] == '16':
            host = pay[1][1]
            self.port = int(host[host.rindex(':')+1:])
            self.hostlist = [host[host.index('//')+2:host.rindex(':')]]
            self.conncount = 0
            if self.handlers.has_key('loginreconnect'):
                self.handlers['loginreconnect'](self)
        else:
            if self.handlers.has_key('loginfail'):
                self.handlers['loginfail'](self,pay[1][1])

    def mxit_online(self,hdr,pay):
        msgs = None
        for each in pay[2:]:
            if not msgs:
                if not type(each) is type([]):
                    msgs = [each.split('\x02')[1]]
                    continue
                if self.dumpProtocol: print 'online',repr(each)
                if type(each) == type([]):
                    if len(each) == 5:
                        [group, jid, nick, status, xport] = each
                        if status != '0':
                            typ = None
                            if status == '2':
                                typ = 'away'
                            elif status == '4':
                                typ = 'dnd'
                            elif status == '5':
                                typ = 'xa'
                            elif status == '7':
                                typ = 'invisible'
                            self.roster[jid]=('available', typ, nick)
                            if self.handlers.has_key('online'):
                                self.handlers['online'](self,jid)
                        else:
                            self.roster[jid]=('unavailable', None, None)
                            if self.handlers.has_key('offline'):
                                self.handlers['offline'](self,jid)
            else:
                if type(each) is type([]) or not '\x02' in each:
                    msgs.append(each)
                    continue
                msgs.append(each.split('\x02')[0])
                self.mxit_msg(hdr, msgs)
                msgs = [each.split('\x02')[1]]

    def mxit_roster(self,hdr,pay):
        if pay[0].has_key(3):
            if pay[0].has_key(14):
                msg = pay[0][14]
            else:
                msg = ''
            if self.handlers.has_key('subscribe'):
                self.handlers['subscribe'](self,pay[0][3],msg)
        self.mxit_online(hdr,pay)

    def mxit_addbuddy(self,hdr,pay):
        pass

    def mxit_msg(self, hdr, pay):
        msgs = pay[3].split('\x02')
        if len(msgs) == 1:
            ts = pay[2][1]
        else:
            ts = None
        if self.handlers.has_key('message'):
            self.handlers['message'](self, pay[2][0], msgs[0], ts)

    def mxit_send_login(self):
        pay = mxit_mkargu({'ms':[self.password,'E-5.0.3-J-j2me',1,'',self.clientkey,'255','27'],'cr':'v5_6'})
        hdr = mxit_mkhdr(len(pay),M_login,0,self.session)
        pkt = hdr + pay
        return pkt

    def mxit_send_addbuddy(self, nick, msg=''):
        if msg == None:
            msg = ''
        #TODO
        #pay = mxit_mkargu({1:self.username,7:nick,65:"jabber_yt",14:msg})
        #hdr = mxit_mkhdr(len(pay), M_rosteradd,1,self.session)
        #return hdr+pay

    def mxit_send_message(self, nick, msg):
        pay = mxit_mkargu({'ms':[nick,msg,1]})
        hdr = mxit_mkhdr(len(pay), M_sendmsg,1,self.session)
        return hdr+pay

    def mxit_send_delbuddy(self, nick, msg=''):
        if msg == None:
            msg = ''
        bgroup = 'jabber_yt'
        for group in self.buddylist.keys():
            for (bjid,bnick) in self.buddylist[group]:
                if bnick == nick in self.buddylist[group]:
                    bgroup = group
        #TODO
        #pay = mxit_mkargu({1:self.username,7:nick,65:bgroup,14:msg})
        #hdr = mxit_mkhdr(len(pay), M_rosterdel,0,self.session)
        #return hdr+pay

    def mxit_send_online(self, show = None, message = None):
        d = '1'
        if show == 'away':
            d = '2'
        elif show == 'dnd':
            d = '4'
        elif show == 'xa':
            d = '5'
        elif show == 'invisible':
            d = '7'
        if self.dumpProtocol: print "send_online",d
        pay = mxit_mkargu({'ms':d})
        hdr = mxit_mkhdr(len(pay),M_status,0,self.session)
        pkt = hdr + pay
        return pkt

    def mxit_send_offline(self):
        if self.dumpProtocol: print "send_offline"
        pay = mxit_mkargu({'ms':'0'})
        hdr = mxit_mkhdr(len(pay),M_logout,0,self.session)
        pkt = hdr + pay
        return pkt

    def Process(self):
        r = self.sock.recv(1024)
        #print r
        if len(r) != 0:
            self.rbuf = '%s%s'%(self.rbuf,r)
            #print len(self.rbuf)
        else:
            # Broken Socket Case.
            if self.handlers.has_key('closed'):
                self.handlers['closed'](self)
        while len(self.rbuf) >= 5:
            s,u = mxit_dehdr(self.rbuf)
            if s[0] != 'ln' or s[2] < 0:
                print 'woops, something went wrong',repr(s),repr(u)
                if self.handlers.has_key('closed'):
                    self.handlers['closed'](self)
                    break
            size = s[1]+s[2]
            #print size, len(self.rbuf)
            if len(self.rbuf) >= size:
                try:
                    t = mxit_deargu(u[:s[2]])
                    s[3] = int(t[0])
                except:
                    traceback.print_exc()
                    print "Broken connection Terminating"
                    if self.handlers.has_key('closed'):
                        self.handlers['closed'](self)
                if self.dumpProtocol: print 'recv', s, t, len(self.rbuf)
                if s[3] == M_login:           #1
                    # login ok
                    self.mxit_login(s,t)
                #elif s[3] == M_challenge:       #84
                #    # login failed
                #    self.mxit_recv_challenge(s,t)
                elif s[3] == M_online:          #3
                    self.mxit_online(s,t)
                elif s[3] == M_roster:          #??
                    self.mxit_roster(s,t)
                elif s[3] == M_recvmsg:         #9
                    self.mxit_msg(s,t)
                #elif s[3] == M_sendmsg:         #10
                #    self.mxit_msg(s,t)
                elif s[3] == M_rosteradd:     #131
                    self.mxit_addbuddy(s,t)
                else:
                    pass
                #print "remove packet"
                self.rbuf = self.rbuf[size:]

            else:
                break

if __name__ == '__main__':
    mxit = MXitCon('MXitID','password','2412345678-1234-1234-1234-123456788901','jid','',True)
    while not mxit.connect():
        print 'sleep'
        time.sleep(5)

    print "connected ", mxit .sock
    mxit.sock.send(mxit.mxit_send_login())

    while 1:
        mxit.Process()

