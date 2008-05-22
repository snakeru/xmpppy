#! /usr/bin/env python

# Yahoo Definitions
import struct

#Packet Types
Y_online = 1        # User online
Y_offline = 2       # User offline
Y_away = 3          # Friend Away
Y_available = 4     # Friend Available
Y_msg = 6           # Instant Message
Y_setaway = 7       # User Away
Y_status = 10       # Friend Status
Y_mail = 11         # Mail
Y_calendar = 13     # A calendar event
Y_roster = 15       # Friend List Change
Y_ping2 = 18        # Secondary Ping
Y_imvset = 21       # IMVironment Setting
Y_invfail = 23      # Invite Failed
Y_confinv = 24      # Conference Invite
Y_confacc = 25      # Conference Accept
Y_conftxt = 26      # Conference Text
Y_confmsg = 27      # Conference Message
Y_confon = 30       # Conference User Online
Y_confoff = 31      # Conference User Offline
Y_confpm = 32       # Conference Instant Message
Y_fileup = 70       # File Transfer Upload
Y_voiceinv = 74     # Voice Chat Invite
Y_notify = 75       # Notification
Y_init = 76         # Initiation
Y_feature = 77      # Extra features
Y_challenge = 84    # Challenge Packet
Y_login = 85        # Login
Y_chalreq = 87      # Challenge Request Packet
Y_rosteradd = 131   # Add Friend
Y_rosterdel = 132   # Remove Friend
Y_ignore = 133      # Ignore
Y_reqroom = 150     # Request Room
Y_gotoroom = 151    # Goto Room
Y_joinroom = 152    # Join Room
Y_leaveroom = 155   # Leave Room
Y_inviteroom = 157  # Invite Room
Y_chatlogout = 160      # Logout
Y_ping = 161        # Primary Ping
Y_chtmsg = 168      # Chat Message
Y_avatar = 188      # Avatar Image update
Y_statusupdate = 198 #update of status (like away/back etc)
Y_advstatusupdate = 199 #update of advanced status (like avatar etc)
Y_cloud = 241       # 0 = Yahoo!, 2 = LiveID (WLM)

Yahoosep = '\xc0\x80'

def ymsg_mkhdr(version, length, packettype, status, sessionid):
    # Make 20 byte yahoo header
    return struct.pack("!4slhhll", "YMSG", version, length, packettype, status, sessionid)
    
def ymsg_dehdr(text):
    # Unpack yahoo header into list
    return [struct.unpack("!4slhhll", text[0:20]),text[20:]]
    
def ymsg_deargu(text):
    # Unpack arguments into dict
    list = text.split(Yahoosep)
    d = {0:{}}
    count = 0
    while list:
        try:
           n = int(list.pop(0))
        except:
            pass
        if list:
            if d[count].has_key(n):
##                if type(d[n]) != type([]):
##                    d[n] = [d[n]]
##                d[n].append(list.pop(0))
                count = count + 1
                d[count]={}
            d[count][n]=list.pop(0)
    return d
    
def ymsg_mkargu(dict):
    # Turn dict into Yahoo Argument string.
    s=''
    for each in dict.keys():
        s=s+'%d%s%s%s' %(each,Yahoosep,dict[each],Yahoosep)
    return s
    
        
