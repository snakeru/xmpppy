#!/usr/bin/python
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# Configuration reader for xmppd.py

# $Id: config.py,v 1.1 2004-09-17 19:53:01 snakeru Exp $

from xmpp import *
import ConfigParser

cfgfile='xmppd.cfg'

class Config(PlugIn):
    def __init__(self):
        PlugIn.__init__(self)
        self.DBG_LINE='config'

    def plugin(self,server):
        configfile = ConfigParser.ConfigParser()
        configfile.add_section('server')
        configfile.readfp(open('xmppd.cfg','r'))
        server.servernames=[]
        for name in configfile.get('server','servername').split(','):
            server.servernames.append(name.strip())
        server.sslcertfile=configfile.get('server','ssl-cert')
