# $Id: __init__.py,v 1.3 2004-10-03 17:46:25 snakeru Exp $

import os
#from psyco.classes import *

for m in os.listdir('modules'):
    if m[:2]=='__' or m[-3:]<>'.py': continue
    exec "import "+m[:-3]

addons = [
# System stuff
    config.Config,
    db_fake.AUTH,
    db_fake.DB,

# XMPP-Core
    stream.TLS,
    stream.SASL,

# XMPP-IM
    stream.Bind,
    stream.Session,
#    privacy.Privacy,
    router.Router,

# JEPs
#    jep0077.IBR,
    jep0078.NSA,
    ]
