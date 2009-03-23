#! /usr/bin/env python

# MXit Definitions
import struct

#Packet Types
M_login = 1         # Login
M_logout = 2        # Logout
M_online = 3        # User online
M_ping = 9          # Keep alive (c2s)
M_recvmsg = 9       # Instant Message (s2c)
M_sendmsg = 10      # Instant Message (c2s)
M_register = 11     # Register
M_status = 32       # User Status

# These are all 'wrong' because they're copies of the yahoo ones just renamed
M_roster = 99       # Friend List Change
M_rosteradd = 131   # Add Friend
M_rosterdel = 132   # Remove Friend

def mxit_mkhdr(length, packettype, status, sessionid):
    # Make mxit header
    data = '\x00id=%s\x00cm=%s' % (sessionid, packettype)
    return 'ln=%s%s' % (len(data) + length - 1, data)

def mxit_dehdr(text):
    # Unpack mxit header into list
    zeroat = text.find('\x00')
    if zeroat < 0: return [[0,0,0,0],'']
    hdr = text[:zeroat].split('=')
    return [[hdr[0],zeroat+1,int(hdr[1]),0],text[zeroat+1:]]

def mxit_deargu(text, sepord=0):
    # Unpack arguments into list
    if sepord > 10 or text.find(chr(sepord)) == -1: return text
    list = text.split(chr(sepord))
    d = []
    for each in list:
        d = d + [mxit_deargu(each, sepord + 1)]
    return d

def mxit_mkargu(dict):
    # Turn dict into MXit Argument string.
    s=''
    for each in dict:
        s=s+'\x00%s=%s' %(each[0],mxit_mklist(each[1]))
    return s

def mxit_mklist(list,sepord=1):
    # Turn args into MXit Argument string.
    if type(list) != type([]): return list
    s=''
    for each in list:
        s=s+'%s%s' %(chr(sepord),each)
    return s[1:]
