# -*- coding: UTF-8 -*-
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# Copyright (C) Kristopher Tate / BlueBridge Technologies Group 2005
# router, presence tracker and probes responder for xmppd.py

from xmpp import *
from xmppd import *

class Router(PlugIn):
    """ The first entity that gets access to arrived stanza. """
    NS='presence'
    def plugin(self,server):
        self._data = {}
        server.Dispatcher.RegisterHandler('presence',self.presenceHandler,xmlns=NS_CLIENT)
        server.Dispatcher.RegisterNamespaceHandler(NS_CLIENT,self.routerHandler)
        server.Dispatcher.RegisterNamespaceHandler(NS_SERVER,self.routerHandler)

    def presenceHandler(self,session,stanza,raiseFlag=True,fromLocal=False):
        self.DEBUG('Presence handler called (%s::%s)' % (session.peer,stanza.getType()),'info')
#       filter out presences that should not influate our 'roster'
#       This is presences, that's addressed:
#        1) any other server
#        2) any user
        to=stanza['to']
        internal = stanza.getAttr('internal')
        #<presence to="test3@172.16.0.2" from="test2@172.16.1.34/Adium" type="probe" />
        if to and (to.getDomain() not in self._owner.servernames) and internal != 'True': return
        
        typ=stanza.getType()
        jid=session.peer #172.16.1.34
        fromOutside = False
        try:
            barejid,resource=jid.split('/')
        except:
            fromOutside = True
            self.DEBUG('Presence: Could not set barejid, fromOutside=True','warn')
            
        if not typ or typ=='available' and fromOutside == False:
            if not self._data.has_key(barejid): self._data[barejid]={}
            if not self._data[barejid].has_key(resource): self._data[barejid][resource]=Presence(frm=jid,typ=typ)
            bp=self._data[barejid][resource]

            try: priority=int(stanza.getTagData('priority'))
            except: priority=0
            bp.T.priority=`priority`
            self._owner.activatesession(session)

            show=stanza.getTag('show')
            if show: bp.T.show=show
            else: bp.T.show=''
            status=stanza.getTag('status')
            if status: bp.T.status=status
            else: bp.T.status=''
            bp.setTimestamp()
            self.update(barejid)
            
            self.broadcastAvailable(session) # Pass onto broadcaster!
            
        elif (typ=='unavailable' or typ=='error') and fromOutside == False:
        
            jid_info = self._owner.tool_split_jid(barejid)
            contacts = session.getRoster()
            for k,v in contacts.iteritems():
                if v['subscription'] in ['from','both']:
                    self.DEBUG('Un-Presence attempt for contact "%s":'%k,'warn')
                    p = Presence(to=k,frm=session.peer,typ='unavailable')
                    status=stanza.getTag('status')
                    if status: p.T.show=status
                    else: p.T.show='Logged Out'
                    self._owner.Dispatcher.dispatch(p,session)
                    self.DEBUG('Finished for "%s"'%k,'info')

            if not self._data.has_key(barejid) and raiseFlag == True: raise NodeProcessed
            if self._data[barejid].has_key(resource): del self._data[barejid][resource]
            self.update(barejid)
            if not self._data[barejid]: del self._data[barejid]
            self._owner.deactivatesession(session.peer)

        elif typ=='invisible' and fromOutside == False:
        
            jid_info = self._owner.tool_split_jid(barejid)
            contacts = session.getRoster()
            for k,v in contacts.iteritems():
                self.DEBUG('Un-Presence attempt for contact [INVISIBLE!!!]"%s":'%k,'warn')
                p = Presence(to=k,frm=session.peer,typ='unavailable')
                status=stanza.getTag('status')
                if status: p.T.show=status
                else: p.T.show='Logged Out'
                session.dispatch(p)
                self.DEBUG('Finished for "%s" [INVISIBLE!!!]'%k,'info')
            
        elif typ=='probe':
            self.DEBUG('Probe activated!','info')
            if stanza.getTo() in self._owner.servernames:
                session.enqueue(Presence(to=stanza.getFrom(),frm=stanza.getTo()))
                raise NodeProcessed
            if stanza.getAttr('internal') == 'True':
                self.DEBUG('Internal Probe activated!','info')
                try:
                    resources=[stanza.getTo().getResource()]
                    if not resources[0]: resources=self._data[stanza.getTo()].keys()
                    flag=1
                    for resource in resources:
                        p=Presence(to=stanza.getFrom(),frm='%s/%s'%(stanza.getTo(),resource),node=self._data[stanza.getTo()][resource])
                        if flag:
                            self._owner.Privacy(session,p)
                            flag=None
                        session.enqueue(p)
                except KeyError: pass #Wanted session is not active! #session.enqueue(Presence(to=stanza.getTo(),frm=jid,typ='unavailable'))
            else:
                self.DEBUG('##SOMETHING IS A MISS IN THE PROBE SUBSYSTEM?##','error')

            

        else: 
            self.DEBUG('Woah, nothing to call???','warn')
        if raiseFlag: raise NodeProcessed

    def broadcastAvailable(self,session,to=None):
        try:
            barejid,resource=session.peer.split('/')
        except:
            fromOutside = True
            self.DEBUG('Presence: Could not set barejid, fromOutside=True','warn')
        
        contacts = session.getRoster()
        for x,y in contacts.iteritems():
            x_split = self._owner.tool_split_jid(x)
            self.DEBUG('Presence attempt for contact "%s":'%x,'warn')
            try:
                if y['subscription'] in ['from','both']:
                    if x_split[1] not in self._owner.servernames or self._owner.DB.pull_roster(x_split[1],x_split[0],barejid) != None:
                        self.DEBUG('Contact "%s" has from/both'%x,'warn')
                        session.dispatch(Presence(to=x,frm=session.peer,node=self._data[barejid][session.getResource()]))
                        self.DEBUG('Finished for "%s"'%x,'info')
                if y['subscription'] in ['to','both']:
                    if (x_split == None and x in self._owner.servernames) or x_split[1] not in self._owner.servernames or self._owner.DB.pull_roster(x_split[1],x_split[0],barejid) != None:
                        self.DEBUG('Contact "%s" has to/both'%x,'warn')
                        p = Presence(to=x,frm=session.peer,typ='probe')
                        p.setAttr('type','probe')
                        session.dispatch(p)
                        self.DEBUG('Finished for "%s"'%x,'info')
            except Exception, err:
                self.DEBUG("PRESENCE_BROADCAST_ERR: %s\nx:%s\ny:%s"%(err,x,y),'error')

    def update(self,barejid):
        pri=-1
        s=None
        for resource in self._data[barejid].keys():
            rpri=int(self._data[barejid][resource].getTagData('priority'))
            if rpri>pri: s=self._owner.getsession(barejid+'/'+resource)
        if s: 
            self._owner.activatesession(s,barejid)
        else:
            self._owner.deactivatesession(barejid)

            

    def safeguard(self,session,stanza):
        if stanza.getNamespace() not in [NS_CLIENT,NS_SERVER]: return # this is not XMPP stanza

        if session._session_state<SESSION_AUTHED: # NOT AUTHED yet (stream's stuff already done)
            session.terminate_stream(STREAM_NOT_AUTHORIZED)
            raise NodeProcessed

        frm=stanza['from']
        to=stanza['to']
        if stanza.getNamespace()==NS_SERVER:
            if not frm or not to \
              or frm.getDomain()!=session.peer \
              or to.getDomain()!=session.ourname:
                session.terminate_stream(STREAM_IMPROPER_ADDRESSING)
                raise NodeProcessed
        else:
            if frm and frm!=session.peer:   # if the from address specified and differs
                if frm.getResource() or not frm.bareMatch(session.peer): # ...it can differ only while comparing inequally
                    session.terminate_stream(STREAM_INVALID_FROM)
                    raise NodeProcessed

            if session._session_state<SESSION_BOUND: # NOT BOUND yet (bind stuff already done)
                if stanza.getType()!='error': session.send(Error(stanza,ERR_NOT_AUTHORIZED))
                raise NodeProcessed

            if name=='presence' and session._session_state<SESSION_OPENED:
                if stanza.getType()!='error': session.send(Error(stanza,ERR_NOT_ALLOWED))
                raise NodeProcessed
            stanza.setFrom(session.peer)
    
    def balance_of_presence(self,session,stanza):
        "Figures-out what should be done to a particular contact"
        self.DEBUG('###BoP: SYSTEM PASS-THROUGH INSTIGATED [%s]'%unicode(stanza).encode('utf-8'),'warn')
        #Predefined settings
#        ["subscribe", "subscribed", "unsubscribe", "unsubscribed"]

        #Stanza Stuff
        try:
            frm=stanza['from']
            frm_node=frm.getNode()
            frm_domain=frm.getDomain()
            outfrom=frm_node+'@'+frm_domain
            self.DEBUG('###BoP: RECIEVED STANZA WITH \'FROM\' ATTR','warn')
        except:
            frm = None
            self.DEBUG('###BoP: RECIEVED STANZA WITHOUT \'FROM\' ATTR','warn')
        session_jid = session.getSplitJID()
        to=stanza['to']
        if not to: return # Not for us.
        to_node=to.getNode()
        if not to_node: return # Yep, not for us.
        to_domain=to.getDomain()
        bareto=to_node+'@'+to_domain

    # 1. If the user wants to request a subscription to the contact's presence information,
    #    the user's client MUST send a presence stanza of type='subscribe' to the contact:

        if stanza.getType() == 'subscribe':
            if session_jid[1] in self._owner.servernames and frm == None:
                self.DEBUG('###BoP: TYP=SUBSCRIBE;U->C','warn')

    # 2. As a result, the user's server MUST initiate a second roster push to all of the user's
    #    available resources that have requested the roster, setting the contact to the pending
    #    sub-state of the 'none' subscription state; this pending sub-state is denoted by the
    #    inclusion of the ask='subscribe' attribute in the roster item:
    #
    #    Note: If the user did not create a roster item before sending the subscription request,
    #          the server MUST now create one on behalf of the user:

                """
                <iq type='set' id='set1'>
                  <query xmlns='jabber:iq:roster'>
                    <item
                        jid='contact@example.org'
                        subscription='none'
                        ask='subscribe'>
                    </item>
                  </query>
                </iq>
                """

                rsess = Iq(typ='set')
                rsess.T.query.setNamespace(NS_ROSTER)
                newitem = rsess.T.query.NT.item
                newitem.setAttr('jid',bareto)
                newitem.setAttr('ask','subscribe')
                # Subscription?
                #Dispatch?
                session.dispatch(rsess)
                #self._owner.ROSTER.RosterAdd(session,rsess) #add to roster!
                
                #{'attr':{'ask':'subscribe'}}
                self._owner.ROSTER.RosterPushOne(session,stanza) #We'll let roster services take the bullet.

        # 3. The user's server MUST also stamp the presence stanza of type "subscribe" with the user's
        #    bare JID (i.e., <user@example.com>) as the 'from' address (if the user provided a 'from'
        #    address set to the user's full JID, the server SHOULD remove the resource identifier). If
        #    the contact is served by a different host than the user, the user's server MUST route the
        #    presence stanza to the contact's server for delivery to the contact (this case is assumed
        #    throughout; however, if the contact is served by the same host, then the server can simply
        #    deliver the presence stanza directly):
        
                stanza.setFrom(session.getBareJID())
                self.DEBUG('###BoP: TYP=SUBSCRIBE;U->C [DONE]','warn')
            elif to_domain in self._owner.servernames and frm != None:
                self.DEBUG('###BoP: THE UN-EXPECTED WAS TRIGGERED','warn')
                pass
        elif stanza.getType() == 'subscribed':
        
        # 5. As a result, the contact's server (1) MUST initiate a roster push to all available resources
        #    associated with the contact that have requested the roster, containing a roster item for the
        #    user with the subscription state set to 'from' (the server MUST send this even if the contact
        #    did not perform a roster set); (2) MUST return an IQ result to the sending resource indicating
        #    the success of the roster set; (3) MUST route the presence stanza of type "subscribed" to the user,
        #    first stamping the 'from' address as the bare JID (<contact@example.org>) of the contact; and
        #    (4) MUST send available presence from all of the contact's available resources to the user:        
            """
            <iq type='set' to='contact@example.org/resource'>
              <query xmlns='jabber:iq:roster'>
                <item
                    jid='user@example.com'
                    subscription='from'
                    name='SomeUser'>
                  <group>SomeGroup</group>
                </item>
              </query>
            </iq>
            """
            if session_jid[1] in self._owner.servernames and frm != None:
                self.DEBUG('###BoP: TYP=SUBSCRIBED;C->U','warn')
                roster = self._owner.DB.pull_roster(session_jid[1],session_jid[0],bareto)
                if roster == None:
                    self.DEBUG('###BoP: TYP=SUBSCRIBED;U->C [NO ROSTER; KILLING NODEPROCESS!','error')
                    raise NodeProcessed
                rsess = Iq(typ='set')
                rsess.T.query.setNamespace(NS_ROSTER)
                newitem = rsess.T.query.NT.item
                newitem.setAttr('jid',bareto)
                self.DEBUG('###BoP: TYP=SUBSCRIBED;U->C SUBSCRIPTION=%s'%roster['subscription'],'warn')
                if roster['subscription'] != 'to':
                    self.DEBUG('###BoP: TYP=SUBSCRIBED;U->C [TO IS NOT ACTIVE!]','warn')
                    newitem.setAttr('subscription','from')
                else:
                    self.DEBUG('###BoP: TYP=SUBSCRIBED;U->C [TO IS ACTIVE!]','warn')
                    newitem.setAttr('subscription','both')
                newitem.setAttr('ask','InternalDelete')
                self._owner.ROSTER.RosterAdd(session,rsess) #add to roster!
    
                self._owner.ROSTER.RosterPushOne(session,stanza) #,{'attr':{'ask':'subscribe'}})
                barejid = session.getBareJID()
                stanza.setFrom(barejid)
                session.dispatch(stanza)
                s=None
                for resource in self._data[barejid].keys():
                    s=self._owner.getsession(barejid+'/'+resource)
                    if s: self.broadcastAvailable(s)
                self.DEBUG('###BoP: TYP=SUBSCRIBED;C->U [DONE]','warn')
                self.DEBUG('###BoP: PASS-THROUGH COMPLETE','warn')
                raise NodeProcessed
                return session,stanza

        # 6. Upon receiving the presence stanza of type "subscribed" addressed to the user, the user's
        #    server MUST first verify that the contact is in the user's roster with either of the following
        #    states: (a) subscription='none' and ask='subscribe' or (b) subscription='from' and ask='subscribe'.
        #    If the contact is not in the user's roster with either of those states, the user's server MUST
        #    silently ignore the presence stanza of type "subscribed" (i.e., it MUST NOT route it to the user,
        #    modify the user's roster, or generate a roster push to the user's available resources). If the
        #    contact is in the user's roster with either of those states, the user's server (1) MUST deliver
        #    the presence stanza of type "subscribed" from the contact to the user; (2) MUST initiate a roster
        #    push to all of the user's available resources that have requested the roster, containing an updated
        #    roster item for the contact with the 'subscription' attribute set to a value of "to"; and (3) MUST
        #    deliver the available presence stanza received from each of the contact's available resources to
        #    each of the user's available resources:
            elif to_domain in self._owner.servernames and frm == None:
                self.DEBUG('###BoP: TYP=SUBSCRIBED;U->C','warn')
                roster = self._owner.DB.pull_roster(to_domain,to_node,outfrom)
                if roster == None: raise NodeProcessed
                ask_good = False
                subscription_good = False
                from_active = False
                for x,y in roster.iteritems():
                    if x=='ask' and y=='subscribe': ask_good = True
                    if x=='subscription' and y in ['none','from']: subscription_good = True
                    if y == 'from': from_active = True
                    if subscription_good==True and ask_good==True: break
                
                if subscription_good!=True and ask_good!=True: raise NodeProcessed

                rsess = Iq(typ='set')
                rsess.T.query.setNamespace(NS_ROSTER)
                newitem = rsess.T.query.NT.item
                newitem.setAttr('jid',outfrom)
                if from_active == True:
                    self.DEBUG('###BoP: TYP=SUBSCRIBED;U->C [FROM IS ACTIVE!]','warn')
                    newitem.setAttr('subscription','both')
                else:
                    self.DEBUG('###BoP: TYP=SUBSCRIBED;U->C [FROM IS NOT ACTIVE!]','warn')
                    newitem.setAttr('subscription','to')
                newitem.setAttr('ask','InternalDelete')
                self._owner.ROSTER.RosterAdd(session,rsess) #add to roster!
    
                self._owner.ROSTER.RosterPushOne(session,stanza) #,{'attr':{'ask':'subscribe'}})
                self.DEBUG('###BoP: TYP=SUBSCRIBED;U->C [DONE]','warn')
        elif stanza.getType() == 'unsubscribe':

            if session_jid[1] in self._owner.servernames and frm == None:
                self.DEBUG('###BoP: TYP=UNSUBSCRIBE;U->C','warn')
                roster = self._owner.DB.pull_roster(session_jid[1],session_jid[0],bareto)
                if roster == None: raise NodeProcessed
                rsess = Iq(typ='set')
                rsess.T.query.setNamespace(NS_ROSTER)
                newitem = rsess.T.query.NT.item
                newitem.setAttr('jid',outfrom)
                if roster['subscription'] == 'both':
                    newitem.setAttr('subscription','from')
                else:
                    newitem.setAttr('subscription','none')
                newitem.setAttr('ask','InternalDelete')
                self._owner.ROSTER.RosterAdd(session,rsess) #add to roster!
    
                self._owner.ROSTER.RosterPushOne(session,stanza) #,{'attr':{'ask':'subscribe'}})
                self.DEBUG('###BoP: TYP=UNSUBSCRIBE;U->C [DONE]','warn')

            if to_domain in self._owner.servernames and frm != None:
                self.DEBUG('###BoP: TYP=UNSUBSCRIBE;C->U','warn')
                roster = self._owner.DB.pull_roster(to_domain,to_node,outfrom)
                if roster == None: raise NodeProcessed
                rsess = Iq(typ='set')
                rsess.T.query.setNamespace(NS_ROSTER)
                newitem = rsess.T.query.NT.item
                newitem.setAttr('jid',outfrom)
                if roster['subscription'] == 'both':
                    newitem.setAttr('subscription','to')
                else:
                    newitem.setAttr('subscription','none')
                newitem.setAttr('ask','InternalDelete')
                self._owner.ROSTER.RosterAdd(session,rsess) #add to roster!
    
                self._owner.ROSTER.RosterPushOne(session,stanza) #,{'attr':{'ask':'subscribe'}})
                self.DEBUG('###BoP: TYP=UNSUBSCRIBE;C->U [DONE]','warn')
        elif stanza.getType() == 'unsubscribed':
            self.DEBUG('###BoP: TYP=UNSUBSCRIBED','warn')

        # 1. If the contact wants to refuse the request, the contact's client MUST send a presence stanza of
        #    type "unsubscribed" to the user (instead of the presence stanza of type "subscribed" sent in Step
        #    6 of Section 8.2):
        
        # 2. As a result, the contact's server MUST route the presence stanza of type "unsubscribed" to the user,
        #    first stamping the 'from' address as the bare JID (<contact@example.org>) of the contact:
            if session_jid[1] in self._owner.servernames and frm == None:
                stanza.setFrom(session.getBareJID())

        #   Note: If the contact's server previously added the user to the contact's roster for tracking purposes,
        #         it MUST remove the relevant item at this time.
                self._owner.DB.del_from_roster(session_jid[1],session_jid[0],bareto)

        # 3. Upon receiving the presence stanza of type "unsubscribed" addressed to the user, the user's server
        #    (1) MUST deliver that presence stanza to the user and (2) MUST initiate a roster push to all of the
        #    user's available resources that have requested the roster, containing an updated roster item for the
        #    contact with the 'subscription' attribute set to a value of "none" and with no 'ask' attribute:

            if to_domain in self._owner.servernames and frm != None:
                self.DEBUG('###BoP: TYP=UNSUBSCRIBED;C->U','warn')
                roster = self._owner.DB.pull_roster(to_domain,to_node,outfrom)
                if roster == None: raise NodeProcessed
                rsess = Iq(typ='set')
                rsess.T.query.setNamespace(NS_ROSTER)
                newitem = rsess.T.query.NT.item
                newitem.setAttr('jid',outfrom)
                if roster['subscription'] == 'to':
                    newitem.setAttr('subscription','none')
                elif roster['subscription'] == 'both':
                    newitem.setAttr('subscription','from')
                else:
                    newitem.setAttr('subscription','none')
                newitem.setAttr('ask','InternalDelete')
                self._owner.ROSTER.RosterAdd(session,rsess) #add to roster!
    
                self._owner.ROSTER.RosterPushOne(session,stanza) #,{'attr':{'ask':'subscribe'}})
                p=Presence(to=outfrom,frm=bareto,typ='unavailable')
                p.setNamespace(NS_CLIENT)
                session.dispatch(p)
                self.DEBUG('###BoP: TYP=UNSUBSCRIBED;C->U [DONE]','warn')

        self.DEBUG('###BoP: PASS-THROUGH COMPLETE','warn')
        return session,stanza
    
    def karmatize_me_captain(self,s,stanza):
            karma = s.getKarma()
            data_len = len(str(stanza))
            if karma != None and time.time() - karma['last_time'] >= 60: # reset counters and stuff!
                karma['last_time'] == time.time()
                karma['tot_up'] = 0
                karma['tot_down'] = 0
            if karma != None and karma['tot_up'] + data_len > karma['up']:
                s.send(Error(stanza,ERR_NOT_ALLOWED))
                raise NodeProcessed
            else:
                if karma != None:
                    karma['tot_up'] += data_len
                    s.updateKarma(karma)
                    
    def routerHandler(self,session,stanza,raiseFlag=True):
        """ XMPP-Core 9.1.1 rules """
        name=stanza.getName()
        self.DEBUG('Router handler called','info')
        
        #Karma stuff!
        self.karmatize_me_captain(session,stanza)
        
        to=stanza['to']
        if stanza.getNamespace()==NS_CLIENT and \
            (not to or to==session.ourname) and \
            stanza.props in ( [NS_AUTH], [NS_REGISTER], [NS_BIND], [NS_SESSION] ):
              return

        if not session.trusted: self.safeguard(session,stanza)

        if not to: return # stanza.setTo(session.ourname)

        domain=to.getDomain()

        getsession=self._owner.getsession
        if domain in self._owner.servernames:
            node=to.getNode()
            if not node: return
            self._owner.Privacy(session,stanza) # it will if raiseFlag: raise NodeProcessed if needed
            bareto=node+'@'+domain
            resource=to.getResource()

# 1. If the JID is of the form <user@domain/resource> and an available resource matches the full JID, 
#    the recipient's server MUST deliver the stanza to that resource.
            try:
                rpri=int(self._data[bareto][resource].getTagData('priority'))
                if rpri<0:
                    session.enqueue(Error(stanza,ERR_SERVICE_UNAVAILABLE))
                    return
            except:
                rpri = None
            if resource and rpri != None and rpri>-1:
                to=bareto+'/'+resource
                s=getsession(to)
                if s:
                    s.enqueue(stanza)
                    if raiseFlag: raise NodeProcessed
# 2. Else if the JID is of the form <user@domain> or <user@domain/resource> and the associated user account 
#    does not exist, the recipient's server (a) SHOULD silently ignore the stanza (i.e., neither deliver it 
#    nor return an error) if it is a presence stanza, (b) MUST return a <service-unavailable/> stanza error 
#    to the sender if it is an IQ stanza, and (c) SHOULD return a <service-unavailable/> stanza error to the 
#    sender if it is a message stanza.
            if not self._owner.AUTH.isuser(node,domain):
                if name in ['iq','message']:
                    if stanza.getType()!='error': session.enqueue(Error(stanza,ERR_SERVICE_UNAVAILABLE))
                if raiseFlag: raise NodeProcessed
# 3. Else if the JID is of the form <user@domain/resource> and no available resource matches the full JID, 
#    the recipient's server (a) SHOULD silently ignore the stanza (i.e., neither deliver it nor return an 
#    error) if it is a presence stanza, (b) MUST return a <service-unavailable/> stanza error to the sender 
#    if it is an IQ stanza, and (c) SHOULD treat the stanza as if it were addressed to <user@domain> if it 
#    is a message stanza.
            if resource and name!='message':
                if name=='iq' and stanza.getType()!='error': session.enqueue(Error(stanza,ERR_SERVICE_UNAVAILABLE))
                if raiseFlag: raise NodeProcessed
# 4. Else if the JID is of the form <user@domain> and there is at least one available resource available 
#    for the user, the recipient's server MUST follow these rules:

            pri=-1
            highest_pri = {'pri':0,'s':None}
            s=None
            try:
                for resource in self._data[bareto].keys():
                    rpri=int(self._data[bareto][resource].getTagData('priority'))
                    if rpri>pri and rpri>=highest_pri['pri']:
                        highest_pri['pri'] = rpri
                        highest_pri['s'] = self._owner.getsession(bareto+'/'+resource)
                        
                if highest_pri['s'] != None:
                    s=highest_pri['s']
                else:
                    s=getsession(to)
            except:
                s=getsession(to)
            if s:
#       1. For message stanzas, the server SHOULD deliver the stanza to the highest-priority available 
#          resource (if the resource did not provide a value for the <priority/> element, the server SHOULD 
#          consider it to have provided a value of zero). If two or more available resources have the same 
#          priority, the server MAY use some other rule (e.g., most recent connect time, most recent 
#          activity time, or highest availability as determined by some hierarchy of <show/> values) 
#          to choose between them or MAY deliver the message to all such resources. However, the server 
#          MUST NOT deliver the stanza to an available resource with a negative priority; if the only 
#          available resource has a negative priority, the server SHOULD handle the message as if there 
#          were no available resources (defined below). In addition, the server MUST NOT rewrite the 'to' 
#          attribute (i.e., it MUST leave it as <user@domain> rather than change it to <user@domain/resource>).
                if name=='message':
                    s.enqueue(stanza)
                    if raiseFlag: raise NodeProcessed
#       2. For presence stanzas other than those of type "probe", the server MUST deliver the stanza to all 
#          available resources; for presence probes, the server SHOULD reply based on the rules defined in 
#          Presence Probes. In addition, the server MUST NOT rewrite the 'to' attribute (i.e., it MUST leave 
#          it as <user@domain> rather than change it to <user@domain/resource>).
               # elif name=='presence' and stanza.getType() == 'probe': # differ to Presence Handler!
                #    return self.presenceHandler(session,stanza,raiseFlag)             
                elif name=='presence':
                    self.DEBUG('Presence stanza detected! (%s)'%stanza['to'],'warn')
                    if stanza.getType() == 'probe' and stanza['to'].getDomain() in self._owner.servernames: 
                        stanza.setAttr('internal','True')
                        self.presenceHandler(session,stanza,raiseFlag)
                        
                    if stanza.getType() in ["subscribe", "subscribed", "unsubscribe", "unsubscribed"]:
                        session,stanza = self.balance_of_presence(session,stanza)
                        
                    # all probes already processed so safely assuming "other" type
                    ps = None
                    for resource in self._data[bareto].keys():
                        ps=getsession(bareto+'/'+resource)
                        if ps: ps.enqueue(stanza)
                    if raiseFlag: raise NodeProcessed
#       3. For IQ stanzas, the server itself MUST reply on behalf of the user with either an IQ result or an 
#          IQ error, and MUST NOT deliver the IQ stanza to any of the available resources. Specifically, if 
#          the semantics of the qualifying namespace define a reply that the server can provide, the server 
#          MUST reply to the stanza on behalf of the user; if not, the server MUST reply with a 
#          <service-unavailable/> stanza error.
                return
# 5. Else if the JID is of the form <user@domain> and there are no available resources associated with 
#    the user, how the stanza is handled depends on the stanza type:
            else:
#       1. For presence stanzas of type "subscribe", "subscribed", "unsubscribe", and "unsubscribed", 
#          the server MUST maintain a record of the stanza and deliver the stanza at least once (i.e., when 
#          the user next creates an available resource); in addition, the server MUST continue to deliver 
#          presence stanzas of type "subscribe" until the user either approves or denies the subscription 
#          request (see also Presence Subscriptions).
                if name=='presence':
                    if stanza.getType() == 'probe' and stanza['to'].getDomain() in self._owner.servernames: 
                        stanza.setAttr('internal','True')
                        self.presenceHandler(session,stanza,raiseFlag)

                    if stanza.getType() in ["subscribe", "subscribed", "unsubscribe", "unsubscribed"]:
                        session,stanza = self.balance_of_presence(session,stanza)
                    #elif stanza.getType() == 'probe': # differ to Presence Handler!
                     #   return self.presenceHandler(session,stanza,raiseFlag)        
#       2. For all other presence stanzas, the server SHOULD silently ignore the stanza by not storing it 
#          for later delivery or replying to it on behalf of the user.
                    if raiseFlag: raise NodeProcessed
#       3. For message stanzas, the server MAY choose to store the stanza on behalf of the user and deliver 
#          it when the user next becomes available, or forward the message to the user via some other means 
#          (e.g., to the user's email account). However, if offline message storage or message forwarding 
#          is not enabled, the server MUST return to the sender a <service-unavailable/> stanza error. (Note: 
#          Offline message storage and message forwarding are not defined in XMPP, since they are strictly a 
#          matter of implementation and service provisioning.)
                elif name=='message':
                    #self._owner.DB.store(domain,node,stanza)
                    if stanza.getType()!='error': session.enqueue(Error(stanza,ERR_RECIPIENT_UNAVAILABLE))
                    if raiseFlag: raise NodeProcessed
#       4. For IQ stanzas, the server itself MUST reply on behalf of the user with either an IQ result or 
#          an IQ error. Specifically, if the semantics of the qualifying namespace define a reply that the 
#          server can provide, the server MUST reply to the stanza on behalf of the user; if not, the server 
 #          MUST reply with a <service-unavailable/> stanza error.
                return
        else:
            s=getsession(domain)
            if not s:
                s=self._owner.S2S(session.ourname,domain)

            s.enqueue(stanza)
            if raiseFlag: raise NodeProcessed
