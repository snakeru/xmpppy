# $Id: __init__.py,v 1.1 2004-09-17 19:53:01 snakeru Exp $

import os
#import sm,config,jep0077,c2s,jep0078
for m in os.listdir('modules'):
    if m[:2]=='__' or m[-3:]<>'.py': continue
    exec "import "+m[:-3]

"""
jabberd2 consists mainly of:
    sm  - XMPP-IM
    c2s - auth and registration
    s2s - jabber:server namespace
"""

addons = [
    config.Config,
    stream.TLS,
#    stream.SASL,
#    c2s.C2S,
#    sm.SM,
    jep0077.IBR,
    jep0078.NSA,
    ]
