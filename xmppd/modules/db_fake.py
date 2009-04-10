
from xmpp import *

db={}

def build_database(server_instance):
    global db
    for a_registered_server in server_instance.servernames:
        server_instance.DEBUG('server','DB: Building database tree for %s'%a_registered_server,'info')
        db[a_registered_server]={}
        
        db[a_registered_server]['test'] = {}
        db[a_registered_server]['test']['storage'] = {'karma':{'down':307200,'up':307200307200307200,'last_time':0.0,'tot_down':0,'tot_up':0}}
        db[a_registered_server]['test']['password'] = 'test'
        #Anon_allow tells the privacy subsystem if it's okay for someone to contact you
        #without any subscription at all.
        db[a_registered_server]['test']['anon_allow'] = 'no'
        db[a_registered_server]['test']['roster'] = {}
        #    {'jid':'test2@172.16.1.34','name':'Test Account 2','subscription':'both'},
        #    {'jid':'test3@172.16.1.34','subscription':'both'}]
        db[a_registered_server]['test']['groups'] = {}
        db[a_registered_server]['test']['groups']['Friends'] = ['test2@172.16.1.34','test3@172.16.1.34']
            
        db[a_registered_server]['test2'] = {}
        db[a_registered_server]['test2']['storage'] = {'karma':{'down':307200,'up':307200,'last_time':0.0,'tot_down':0,'tot_up':0}}
        db[a_registered_server]['test2']['password'] = 'test'
        db[a_registered_server]['test2']['anon_allow'] = 'yes'
        
        db[a_registered_server]['test2']['roster'] = {}
        db[a_registered_server]['test2']['roster']['test3@'+a_registered_server] = {'subscription':'both'}

        db[a_registered_server]['test2']['groups'] = {}
        db[a_registered_server]['test2']['groups']['Friends'] = ['test3@172.16.1.34','test3@172.16.0.2','test3@'+a_registered_server]
        
        db[a_registered_server]['test3'] = {}
        db[a_registered_server]['test3']['storage'] = {'karma':{'down':307200,'up':307200,'last_time':0.0,'tot_down':0,'tot_up':0}}
        db[a_registered_server]['test3']['password'] = 'test'
        db[a_registered_server]['test3']['anon_allow'] = 'yes'
        db[a_registered_server]['test3']['name'] = 'テスト・アカウント#3'
        #Roster Info
        ##Roster Items
        db[a_registered_server]['test3']['roster'] = {}
        db[a_registered_server]['test3']['roster']['test2@'+a_registered_server] = {'subscription':'both'}
        db[a_registered_server]['test3']['roster']['pixelcort@'+a_registered_server] = {'subscription':'both'}
        db[a_registered_server]['test3']['roster']['kris_tate@'+a_registered_server] = {'subscription':'both'}

        ##Item Groups
        db[a_registered_server]['test3']['groups'] = {}
        db[a_registered_server]['test3']['groups']['かっこういいな人'] = ['test2@172.16.1.34','test2@172.16.0.2','test2@'+a_registered_server,'pixelcort@'+a_registered_server,'kris_tate@'+a_registered_server]

        db[a_registered_server]['pixelcort'] = {}
        db[a_registered_server]['pixelcort']['storage'] = {'karma':{'down':307200,'up':307200,'last_time':0.0,'tot_down':0,'tot_up':0}}
        db[a_registered_server]['pixelcort']['password'] = 'test'
        db[a_registered_server]['pixelcort']['anon_allow'] = 'yes'
        db[a_registered_server]['pixelcort']['name'] = 'Cortland Klein'
        #Roster Info
        ##Roster Items
        db[a_registered_server]['pixelcort']['roster'] = {}
        db[a_registered_server]['pixelcort']['roster']['tekcor@'+a_registered_server] = {'subscription':'both'}
        db[a_registered_server]['pixelcort']['roster']['kris_tate@'+a_registered_server] = {'subscription':'both'}
        db[a_registered_server]['pixelcort']['roster']['mvanveen@'+a_registered_server] = {'subscription':'both'}

        ##Item Groups
        db[a_registered_server]['pixelcort']['groups'] = {}
        db[a_registered_server]['pixelcort']['groups']['Friends'] = ['tekcor@'+a_registered_server,'mvanveen@'+a_registered_server]
        db[a_registered_server]['pixelcort']['groups']['Kris'] = ['kris_tate@'+a_registered_server]
        
        db[a_registered_server]['kris_tate'] = {}
        db[a_registered_server]['kris_tate']['storage'] = {'karma':{'down':307200,'up':1000,'last_time':0.0,'tot_down':0,'tot_up':0}}
        db[a_registered_server]['kris_tate']['password'] = 'test'
        db[a_registered_server]['kris_tate']['anon_allow'] = 'yes'
        db[a_registered_server]['kris_tate']['name'] = 'Kristopher Tate'
        #Roster Info
        ##Roster Items
        db[a_registered_server]['kris_tate']['roster'] = {}
        db[a_registered_server]['kris_tate']['roster']['tekcor@'+a_registered_server] = {'subscription':'both'}
        db[a_registered_server]['kris_tate']['roster']['pixelcort@'+a_registered_server] = {'subscription':'both'}
        db[a_registered_server]['kris_tate']['roster']['mvanveen@'+a_registered_server] = {'subscription':'both'}

        ##Item Groups
        db[a_registered_server]['kris_tate']['groups'] = {}
        db[a_registered_server]['kris_tate']['groups']['かっこういいな人'] = ['tekcor@'+a_registered_server,'pixelcort@'+a_registered_server,'mvanveen@'+a_registered_server]

        db[a_registered_server]['tekcor'] = {}
        db[a_registered_server]['tekcor']['storage'] = {'karma':{'down':307200,'up':307200,'last_time':0.0,'tot_down':0,'tot_up':0}}
        db[a_registered_server]['tekcor']['password'] = 'test'
        db[a_registered_server]['tekcor']['anon_allow'] = 'yes'
        db[a_registered_server]['tekcor']['name'] = 'Thom McGrath'
        #Roster Info
        ##Roster Items
        db[a_registered_server]['tekcor']['roster'] = {}
        db[a_registered_server]['tekcor']['roster']['pixelcort@'+a_registered_server] = {'subscription':'both'}
        db[a_registered_server]['tekcor']['roster']['kris_tate@'+a_registered_server] = {'subscription':'both'}

        ##Item Groups
        db[a_registered_server]['tekcor']['groups'] = {}
        db[a_registered_server]['tekcor']['groups']['Friends'] = ['kris_tate@'+a_registered_server,'pixelcort@'+a_registered_server]


        db[a_registered_server]['mvanveen'] = {}
        db[a_registered_server]['mvanveen']['storage'] = {'karma':{'down':307200,'up':307200,'last_time':0.0,'tot_down':0,'tot_up':0}}
        db[a_registered_server]['mvanveen']['password'] = 'test'
        db[a_registered_server]['mvanveen']['anon_allow'] = 'yes'
        db[a_registered_server]['mvanveen']['name'] = 'Mike Van Veen'
        #Roster Info
        ##Roster Items
        db[a_registered_server]['mvanveen']['roster'] = {}
        db[a_registered_server]['mvanveen']['roster']['pixelcort@'+a_registered_server] = {'subscription':'both'}
        db[a_registered_server]['mvanveen']['roster']['kris_tate@'+a_registered_server] = {'subscription':'both'}

        ##Item Groups
        db[a_registered_server]['mvanveen']['groups'] = {}
        db[a_registered_server]['mvanveen']['groups']['Friends'] = ['kris_tate@'+a_registered_server,'pixelcort@'+a_registered_server]
        
        for guy in db[a_registered_server].keys():
            db[a_registered_server][guy]['roster'][a_registered_server] = {'subscription':'to','name':"Help Desk"}
            

class AUTH(PlugIn):
    NS=''
    def getpassword(self, node, domain):
        try: return db[domain][node]['password']
        except KeyError: pass

    def isuser(self, node, domain):
        try: return db[domain].has_key(node)
        except KeyError: pass

class DB(PlugIn):
    NS=''
    
    
    def plugin(self,server):
        self.DEBUG('Building Database tree!','info')
        build_database(server) #Building database!
    def store(self,domain,node,stanza,id='next_unique_id'):
        try:
            self.DEBUG("Storing to database:\n%s:%s::%s:%s"%(domain,node,id,stanza),'info')
            db[domain][node]['storage'][id] = stanza
            return True
        except KeyError:
            self.DEBUG("Could not store in database:\n%s:%s::%s:%s"%(domain,node,id,stanza),'error')
            return False

    def get_store(self,domain,node,id):
        try:
            return db[domain][node]['storage'][id]
        except KeyError:
            return False

    def save(self,domain,node,stanza,id='next_unique_id'):
        try:
            self.DEBUG("Saving to database:\n%s:%s::%s:%s"%(domain,node,id,stanza),'info')
            db[domain][node][id] = stanza
            return True
        except KeyError:
            self.DEBUG("DB ERR: Could not save to database:\n%s:%s::%s:%s"%(domain,node,id,stanza),'error')
            return False
    
    def save_to_roster(self,domain,node,jid,info,add_only_if_already=False):
        self.DEBUG("Saving roster info to database %s-->(%s) [%s]:\n"%(jid,node+'@'+domain,str(info)),'info')
        if db[domain][node]['roster'].has_key(jid) and add_only_if_already==False:
            db[domain][node]['roster'][jid].update(info)
        else:
            db[domain][node]['roster'][jid] = info


    def pull_roster(self,domain,node,jid):
        try:
            data = db[domain][node]['roster'][jid]
            if data.has_key('subscription') == False:
                data.update({'subscription':'none'})
            return data
        except KeyError:
            self.DEBUG('DB ERR: Could not retrieve %s::%s::roster::%s'%(domain,node,jid),'error') 
            return None

    def del_from_roster(self,domain,node,jid):
        self.DEBUG("Deleting roster info from database %s--X(%s):\n"%(jid,node+'@'+domain),'info')
        try:
            del(db[domain][node]['roster'][jid])
            return True
        except KeyError, err:
            self.DEBUG('DB ERR: A Client tried to remove a contact that wasn\'t even added! (%s::%s::%s)'%(domain,node,jid),'error') 
            return False

    def del_from_roster_jid(self,domain,node,jid,what):
        self.DEBUG("Deleting roster info from database %s--X(%s):\n"%(jid,node+'@'+domain),'info')
        try:
            del(db[domain][node]['roster'][jid][what])
            return True
        except KeyError, err:
            self.DEBUG('DB ERR: A Client tried to remove a contact attr that wasn\'t even added! (%s::%s::%s)'%(domain,node,jid),'error') 
            return False

    def save_groupie(self,domain,node,jid,groups):
        temp = []
        for x in groups:
            if type(x)==type(u''): x = x.encode('utf-8')
            elif type(x)==type(u''): x = unicode(x).encode('utf-8')
            temp += [x]
        group_list = x
        self.DEBUG("Saving groupie jid to database %s-->(%s) [%s]:\n"%(jid,node+'@'+domain,unicode(groups).encode('utf-8')),'info')
        for gn,gm in db[domain][node]['groups'].iteritems():
            if gn not in group_list and jid in db[domain][node]['groups'][gn]:
                db[domain][node]['groups'][gn].remove(jid)
            elif gn in group_list and jid not in db[domain][node]['groups'][gn]:
                db[domain][node]['groups'][gn] += [jid]

    def del_groupie(self,domain,node,jid):
        try:
            self.DEBUG("Deleting groupie from database %s--X(%s):\n"%(jid,node+'@'+domain),'info')
            for gn,gm in db[domain][node]['groups'].iteritems():
                if jid in db[domain][node]['groups'][gn]:
                    db[domain][node]['groups'][gn].remove(jid)
        except Exception, err:
            self.DEBUG('DB ERR: A groupie went mad! %s::%s::%s'%(domain,node,jid),'error') 
    
    def get(self,domain,node,what):
        try:
            return db[domain][node][what]
        except KeyError:
            self.DEBUG('DB ERR: Could not retrieve %s::%s::%s'%(domain,node,what),'error') 
            return None

    def delete(self,domain,node,what):
        try:
            del(db[domain][node][what])
            return True
        except KeyError:
            self.DEBUG('DB ERR: Could not delete %s::%s::%s'%(domain,node,what),'error') 
            return None

    def getNumRegistered(self,server):
        return len(db[server].keys())