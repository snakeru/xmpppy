# $Id$

import os
from psyco.classes import *

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
    db_fake.AUTH,
    stream.SASL,
    stream.Bind,
    jep0077.IBR,
    jep0078.NSA,
    ]
