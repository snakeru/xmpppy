# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# Configuration reader for xmppd.py

# $Id: config.py,v 1.3 2004/10/03 17:47:50 snakeru Exp $

from xmpp import *
import ConfigParser

cfgfile='xmppd.cfg'

class Config(PlugIn):
    NS=''
    def __init__(self):
        PlugIn.__init__(self)
        self.DBG_LINE='config'

    def plugin(self,server):
        configfile = ConfigParser.ConfigParser()
        configfile.add_section('server')
        configfile.readfp(open('xmppd.cfg','r'))
        #server names
        server.servernames=[]
        #server admins
        server.administrators={}
        try: server.sqlite_db = configfile.get('server','sqlite_file')
        except: server.sqlite_db = None
        
        
        for name in configfile.get('server','servernames').split(','):
            server.DEBUG('server','Added new server (%s) from config!'%name.split(),'info')
            server.servernames.append(name.strip())
            #configfile.add_section(name)
            server.administrators.update({name:[]})
            for admin in configfile.get(name,'admins').split(','):
                server.DEBUG('server','Added new admin (%s) for server (%s) from config!'%(admin.split(),name),'info')
                server.administrators[name].append(admin.strip())
            
        try: server.sslcertfile=configfile.get('server','ssl-cert')
        except: server.sslcertfile=None
        try: server.sslkeyfile=configfile.get('server','ssl-key')
        except: server.sslkeyfile=server.sslcertfile
