# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# AUTH_db interface example for xmppd.py

# $Id: db_fake.py,v 1.2 2004-10-03 17:48:09 snakeru Exp $

from xmpp import *

db={}
db['localhost']={}
db['80.95.32.177']={}
db['localhost']['test']='test'
db['localhost']['test2']='test'
db['80.95.32.177']['test']='test'

class AUTH(PlugIn):
    NS=''
    def getpassword(self, authzid, authcid):
        try: return db[authzid][authcid]
        except KeyError: pass
    def isuser(self, authzid, authcid):
        try: return db[authzid].has_key(authcid)
        except KeyError: pass

class DB(PlugIn):
    NS=''
    def store(self,domain,node,stanza,id='next_unique_id'): pass
