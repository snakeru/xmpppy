#!/usr/bin/python
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# AUTH_db interface example for xmppd.py

# $Id$

from xmpp import *

db={}
db['localhost']={}
db['localhost']['testuser']='testpassword'

class AUTH(PlugIn):
    def getpassword(self, authzid, authcid):
        try: return db[authzid][authcid]
        except KeyError: pass
