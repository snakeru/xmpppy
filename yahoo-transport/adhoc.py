# $Id$

import sys, xmpp
from xmpp.protocol import *
import config
from jep0133 import *

class AdHocCommands:

    def __init__(self, userfile):
        self.userfile = userfile

    def PlugIn(self, transport):
        self.commands = xmpp.commands.Commands(transport.disco)
        self.commands.PlugIn(transport.jabber)

        # jep-0133 commands:
        transport.cmdonlineusers = Online_Users_Command(transport.userlist,jid=config.jid)
        transport.cmdonlineusers.plugin(self.commands)
        transport.cmdactiveusers = Active_Users_Command(transport.userlist,jid=config.jid)
        transport.cmdactiveusers.plugin(self.commands)
        transport.cmdregisteredusers = Registered_Users_Command(self.userfile,jid=config.jid)
        transport.cmdregisteredusers.plugin(self.commands)
        transport.cmdeditadminusers = Edit_Admin_List_Command(jid=config.jid)
        transport.cmdeditadminusers.plugin(self.commands)
        transport.cmdrestartservice = Restart_Service_Command(transport,jid=config.jid)
        transport.cmdrestartservice.plugin(self.commands)
        transport.cmdshutdownservice = Shutdown_Service_Command(transport,jid=config.jid)
        transport.cmdshutdownservice.plugin(self.commands)

        # transport wide commands:
        transport.cmdconnectusers = Connect_Registered_Users_Command(self.userfile)
        transport.cmdconnectusers.plugin(self.commands)

class Connect_Registered_Users_Command(xmpp.commands.Command_Handler_Prototype):
    """This is the """
    name = "connect-users"
    description = 'Connect all registered users'
    discofeatures = [xmpp.commands.NS_COMMANDS]

    def __init__(self,userfile):
        """Initialise the command object"""
        xmpp.commands.Command_Handler_Prototype.__init__(self,config.jid)
        self.initial = { 'execute':self.cmdFirstStage }
        self.userfile = userfile

    def _DiscoHandler(self,conn,request,type):
        """The handler for discovery events"""
        if request.getFrom().getStripped() in config.admins:
            return xmpp.commands.Command_Handler_Prototype._DiscoHandler(self,conn,request,type)
        else:
            return None

    def cmdFirstStage(self,conn,request):
        """Build the reply to complete the request"""
        if request.getFrom().getStripped() in config.admins:
            for each in self.userfile.keys():
                conn.send(Presence(to=each, frm = config.jid, typ = 'probe'))
                if self.userfile[each].has_key('servers'):
                    for server in self.userfile[each]['servers']:
                        conn.send(Presence(to=each, frm = '%s@%s'%(server,config.jid), typ = 'probe'))
            reply = request.buildReply('result')
            form = DataForm(typ='result',data=[DataField(value='Command completed.',typ='fixed')])
            reply.addChild(name='command',namespace=NS_COMMANDS,attrs={'node':request.getTagAttr('command','node'),'sessionid':self.getSessionID(),'status':'completed'},payload=[form])
            self._owner.send(reply)
        else:
            self._owner.send(Error(request,ERR_FORBIDDEN))
        raise NodeProcessed

