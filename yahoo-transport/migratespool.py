#! /usr/bin/env python

""" Python importer script for migrating from the C based Yahoo transport 

To use run in the directory of the spool files and a user.dbm file will be left in there. 

Only files which are in the form user%server.xml will be processed.

"""

import os
import xmpp
import shelve
userfile = shelve.open('user.dbm')
for each in os.listdir('.'):
    if each[len(each)-4:len(each)] == '.xml':
        b = each[:len(each)-4].split('%')
        if len(b) == 2:
            file = open(each)
            data = file.read()
            xml = xmpp.simplexml.XML2Node(data)
            # Get the items of interest within the iq query
            items = xml.getChildren()[0].getChildren()
            username = None
            password = None
            for item in items:
                if item.name == 'username':
                    username = item.getData()
                elif item.name == 'password':
                    password = item.getData()
            if password !='':
                name = '%s@%s'%(b[0],b[1])
                dict = {'username':username,'password':password,'subscribed':True}
                userfile[name]=dict
                userfile.sync()
                print "Added %s" % name
userfile.sync()
userfile.close()