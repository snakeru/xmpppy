#!/usr/bin/python
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# AUTH_db interface example for xmppd.py

# $Id: db_fake.py,v 1.1 2004-09-19 20:05:22 snakeru Exp $

from xmpp import *

db={}
db['localhost']={}
db['localhost']['testuser']='testpassword'

class AUTH(PlugIn):
    def getpassword(self, authzid, authcid):
        try: return db[authzid][authcid]
        except KeyError: pass
