from xmpp.simplexml import Node
# MRA 20040718

NS_MUC_USER = 'http://jabber.org/protocol/muc#user'
NS_EVENT = 'jabber:x:event'
NS_SI = 'http://jabber.org/protocol/si'
NS_SI_FILE = 'http://jabber.org/prtocol/si/file-transfer'
NS_FEATURE = 'http://jabber.org/protocol/feature-neg'


class MucUser(Node):
    # Muc User Helper
    def __init__(self,status = None, nick = None, jid = None, affiliation = None, role = None, reason = None, actor = None, node = None):
        Node.__init__(self, 'x', node = node)
        if not Node:
            self.setNamespace(NS_MUC_USER)
        if jid != None:
            self.setJid(jid)
        if affiliation != None:
            self.setAffiliation(affiliation)
        if role != None:
            self.setRole(role)
        if nick != None:
            self.setNick(nick)
        if reason != None:
            self.setReason(reason)
        if status != None:    
            self.setStatus(status)
        if actor != None:
            self.setActor(actor)
    def getStatus(self): return self.getTagAttr('status','code')
    def setStatus(self,status): self.setTagAttr('status','code',status)
    def getNick(self): return self.getTagAttr('item','nick')
    def setNick(self,nick): self.setTagAttr('item','nick',nick)
    def getJid(self): return self.getTagAttr('item','jid')
    def setJid(self,jid): self.setTagAttr('item','jid',jid)
    def getAffiliation(self): return self.getTagAttr('item','affiliation')
    def setAffiliation(self,affiliation): self.setTagAttr('item','affiliation',affiliation)
    def getRole(self): return self.getTagAttr('item','role')
    def setRole(self,role): self.setTagAttr('item','role',role)
    def getReason(self):
        try:
            return self.getTag('item').getTagData('reason')
        except AttributeError:
            return None
    def setReason(self,reason):self.setTag('item').setTagData('reason',reason)
    def getActor(self):
        try:
            return self.getTag('item').getTagAttr('actor','jid')
        except AttributeError:
            return None
    def setActor(self,actor): self.setTag('item').setTagAttr('actor','jid',actor)
    def setInvite(self, jid, type, reason):
        # Type should be either 'to' or 'from'
        p = self.setTagAttr('invite',type,jid)
        p.setTagData('reason',reason)
    def setDecline(self, jid, type, reason):
        #Type should be either 'to' or 'from'
        p = self.setTagAttr('decline',type,jid)
        p.setTagData('reason',reason)
        
class Event(Node):
    def __init__(self, id = None, composing = False, delivered = False, offline = False, displayed = False, node = None):
        Node.__init__(self, 'x', node = node)
        if not node:
            self.setNamespace(NS_EVENT)
        if id != None:
            self.setEventID(id)
        if composing:
            self.setComposing()
        if delivered:
            self.setDelivered()
        if offline:
            self.setOffline()
        if displayed:
            self.setDisplayed()
    def setEventID(self,id): self.setTagData('id',id)
    def setComposing(self): self.setTag('composing')
    def setDelivered(self): self.setTag('delivered')
    def setOffline(self): self.setTag('offline')
    def setDisplayed(self): self.setTag('displayed')
    def getEventID(self): return self.getTagData('id')
    def isComposing(self): return self.getTag('composing') != None
    def isOffline(self): return self.getTag('offline') != None
    def isDelivered(self): return self.getTag('delivered') != None
    def isDisplayed(self): return self.getTag('displayed') != None

class FeatureNeg:
    # Feature Negotiation is basically a namespace wrapper around the dataform
    # To use: use getForm to return a form object
    # To send just addChild your form to the object, or include in the parameters 
    def __init__(self, form = None, node = None):
        Node.__init__(self,'feature',node=node)
        if not node:
            self.setNamespace(NS_FEATURE)
        if form:
            self.addChild(form)
    def getForm(self): return DataForm(node=self.getTag('x',namespace=NS_DATA))

class SI(Node):
    # Stream initiation profiles
    # To use:
    # This wrapper class sets all the objects, if using to make new profile fill in the values and add two children.
    # One for the profile and one for the Feature Negotiation
    def __init__(self, id = None, mimetype = None, profile = None, node = None):
        Node.__init__(self,'si',node=node)
        if not node:
            self.setNamespace(NS_SI)
        if id != None:
            self.setID(id)
        if mime-type:
            self.setMimeType(mime-type)
        if profile:
            self.setProfile(profile)
    def setID(self,id): self.setAttr('id',id)
    def setMimeType(self,mimetype): self.setAttr('mime-type',mimetype)
    def setProfile(self,profile): self.setAttr('profile',profile)
    def getID(self): return self.getAttr('id')
    def getMimeType(self): return self.getAttr('mime-type')
    def getProfile(self): return self.getAttr('profile')
    def getProfileObj(self):
        for each in self.getChildren():
            if each.getNamespace() == self.getProfile():
                return each
    def getFeatureNeg(self): return FeatureNeg(self.getTag('feature',namespace=NS_FEATURE))
    
class SI_File(Node):
    def __init__(self, name = None, size = None, hash = None, date = None, offset = None, length = None, node = None):
        Node.__init__(self,'file',node=node)
        if not node:
            self.setNamespace(NS_SI_FILE)
        if name:
            self.setName(name)
        if size:
            self.setSize(size)
        if hash:
            self.setHash(hash)
        if date:
            self.setDate(date)
        if offset:
            self.setOffset(offset)
        if length:
            self.setLength(length)
    def setName(self,name): self.setAttr('name',name)
    def setSize(self,size): self.setAttr('size',size)
    def setHash(self,hash): self.setAttr('hash',hash)
    def setDate(self,date): self.setAttr('date',date)
    def setOffset(self,offset): self.setTagAttr('range','offset',offset)
    def setLength(self,length): self.setTagAttr('range','length',length)
    def getName(self): return self.getAttr('name')
    def getSize(self): return self.getAttr('size')
    def getHash(self): return self.getAttr('hash')
    def getDate(self): return self.getAttr('date')
    def getOffset(self): return self.getTagAttr('range','offset')
    def getLength(self): return self.getTagAttr('range','length')
    
    