#!/usr/bin/python
# Distributed under the terms of GPL version 2 or any later
# Copyright (C) Alexey Nezhdanov 2004
# Stream-level features for xmppd.py

# $Id: stream.py,v 1.2 2004-09-19 20:20:05 snakeru Exp $

from xmpp import *
import socket
from tlslite.api import *

class TLS(PlugIn):
    """ 3.                        <features/>
        4. <starttls/>
        5.                        <proceed/> / <failure/>
        -- NEW STREAM / connection close --
        """
    def plugin(self,server):
        server.Dispatcher.RegisterHandler('starttls',self.starttlsHandler,xmlns=NS_TLS)
        server.Dispatcher.RegisterHandler('proceed',self.proceedfailureHandler,xmlns=NS_TLS)
        server.Dispatcher.RegisterHandler('failure',self.proceedfailureHandler,xmlns=NS_TLS)
        server.Dispatcher.RegisterHandler('features',self.FeaturesHandler,xmlns=NS_STREAMS)
        server.feature(NS_TLS)

    def starttlsHandler(self,session,stanza):
        if 'tls' in session.features:
            session.send(Node('failure',{'xmlns':NS_TLS}))
            self.DEBUG('TLS startup failure: already started.','error')
            session.unfeature(NS_TLS)
            raise NodeProcessed
        if self._owner.__dict__.has_key('sslcertfile'): certfile=self._owner.sslcertfile
        else: certfile=None
        if self._owner.__dict__.has_key('sslkeyfile'): keyfile=self._owner.sslkeyfile
        else: keyfile=certfile
        try: open(certfile) ; open(keyfile)
        except: certfile=None
        if not certfile or not keyfile:
            session.send(Node('failure',{'xmlns':NS_TLS}))
            self.DEBUG('TLS startup failure: can\'t find SSL cert/key file[s].','error')
            session.unfeature(NS_TLS)
            raise NodeProcessed
        session.send(Node('proceed',{'xmlns':NS_TLS}))
        self.startservertls(session)
        session.StartStream()
        raise NodeProcessed

    def startservertls(self,session):
        try:
            cert=open(self._owner.sslcertfile).read()
            key=open(self._owner.sslkeyfile).read()
        except:
            session.unfeature(NS_TLS)
            raise NodeProcessed

        self.DEBUG('Starting server-mode TLS.','ok')
        x509 = X509()
        x509.parse(cert)
        certChain = X509CertChain([x509])
        privateKey = parsePEMKey(key, private=True)
        connection = TLSConnection(session._sock)
        connection.handshakeServer(certChain=certChain, privateKey=privateKey, reqCert=False)

        session._sslObj = connection
        session._recv = connection.read
        session._send = connection.write

        session.feature(NS_TLS)

    def proceedfailureHandler(self,session,stanza):
        if stanza.getName()<>'proceed':
            self.DEBUG('TLS can not be started. Giving up.','error')
            session.unfeature(NS_TLS)
            raise NodeProcessed
        self.DEBUG('Starting client-mode TLS.','ok')
        try: session._sslObj = socket.ssl(session._sock, None, None)
        except:
            session.set_socket_state('SOCKET_DEAD')
            self.DEBUG('TLS failed. Terminating session','error')
            session.terminate_stream()
            raise NodeProcessed
        session._recv = session._sslObj.read
        session._send = session._sslObj.write

        session.feature(NS_TLS)
        session.StartStream()
        raise NodeProcessed

    def FeaturesHandler(self,session,stanza):
        if NS_TLS in session.features: return     # already started. do nothing
        if not stanza.getTag('starttls',namespace=NS_TLS):
            self.DEBUG("TLS unsupported by remote server.",'warn')
        else:
            self.DEBUG("TLS supported by remote server. Requesting TLS start.",'ok')
            session.send(Node('starttls',{'xmlns':NS_TLS}))
        raise NodeProcessed

import sha,base64,random,md5

def HH(some): return md5.new(some).hexdigest()
def H(some): return md5.new(some).digest()
def C(some): return ':'.join(some)

class SASL(PlugIn):
    """ 3.                        <features/>
        4. <auth/>
        5.                        <challenge/> / <failure/>
        6. <response/>
        7.                        <challenge/> / <failure/>
        8. <response/> / <abort/>
        9.                        <success/>   / <failure/>
        feature SASL, unfeature TLS
        -- NEW STREAM on success --

        What to do on failure (remote server rejected us)?
        Probably drop the stream, mark this server as unreachable for several hours and notify admin?
        If client supplied wrong credentials allow him to retry (configurable number of times).
        """

    def plugin(self,server):
        server.Dispatcher.RegisterNamespaceHandler(NS_SASL,self.SASLHandler)
        server.Dispatcher.RegisterHandler('features',self.FeaturesHandler,xmlns=NS_STREAMS)
        self.mechanisms=['PLAIN']#,'DIGEST-MD5']  # for announce in <features/> tag
        server.feature(NS_SASL)

    def startauth(self,session,username,password):
        session.username=username
        session.password=password
        if session.Stream.features:
            try: self.FeaturesHandler(session,session.Stream.features)
            except NodeProcessed: pass

    def FeaturesHandler(self,session,feats):
        if not session.__dict__.has_key('username'): return
        if not feats.getTag('mechanisms',namespace=NS_SASL):
            session.unfeature(NS_SASL)
            self.DEBUG('SASL not supported by server','error')
            return
        mecs=[]
        for mec in feats.getTag('mechanisms',namespace=NS_SASL).getTags('mechanism'):
            mecs.append(mec.getData())
        if "DIGEST-MD5" in mecs:
            node=Node('auth',attrs={'xmlns':NS_SASL,'mechanism':'DIGEST-MD5'})
        elif "PLAIN" in mecs:
            sasl_data='%s\x00%s\x00%s'%(self.username+'@'+session.peer,self.username,self.password)
            node=Node('auth',attrs={'xmlns':NS_SASL,'mechanism':'PLAIN'},payload=[base64.encodestring(sasl_data)])
        else:
            session.startsasl='failure'
            self.DEBUG('I can only use DIGEST-MD5 and PLAIN mecanisms.','error')
            return
        session.startsasl='in-process'
        session.send(node.__str__())
        raise NodeProcessed

    def commit_auth(self,session,authcid):
        session.send(Node('success',{'xmlns':NS_SASL}))
        session.feature(NS_SASL)
        session.unfeature(NS_TLS)
        session.sasl['next']=[]
        session.StartStream()
        session.username=authcid.lower()
        session.set_auth_state('AUTHED')
        self.DEBUG('Peer %s@%s successfully authenticated'%(authcid,session.servername),'ok')

    def reject_auth(self,session,authcid='unknown'):
        session.send(Node('failure',{'xmlns':NS_SASL},[Node('not-authorized')]))
        session.sasl['retries']=session.sasl['retries']-1
        if session.sasl['retries']<=0: session.terminate_stream()
        self.DEBUG('Peer %s@%s failed to authenticate'%(authcid,session.servername),'error')

    def SASLHandler(self,session,stanza):
        """simple username: node _or_ servername
        """
        if NS_SASL in session.features:
            self.DEBUG('Already authorized. Ignoring SASL stanza.','error')
            raise NodeProcessed
        if not session.__dict__.has_key('sasl'):
            session.sasl={'retries':3}
        if not session.sasl.has_key('next'):
            session.sasl={'retries':session.sasl['retries']}
            if session.TYP=='server': session.sasl['next']=['auth']
            else: session.sasl['next']=['challenge','success','failure']
        if stanza.getName() not in session.sasl['next']:
            # screwed SASL implementation on the other side. terminating stream
            session.terminate_stream(ERR_BAD_REQUEST)
            raise NodeProcessed
        #=================== preparation ===============================================
        try: data=base64.decodestring(stanza.getData())
        except:
            session.terminate_stream(ERR_BAD_REQUEST)
            raise NodeProcessed
        self.DEBUG('Got challenge:'+data,'ok')
        for pair in data.split(','):
            if pair.find('=')==-1:
                session.sasl['otherdata']=pair
                continue
            key,value=pair.split('=',1)
            if value[:1]=='"' and value[-1:]=='"': value=value[1:-1]
            if key in ['qop','username','realm','nonce','cnonce','digest-uri',
                       'nc','response','charset','rspauth','algorithm']:
                chal[key]=value
        #=================== SASL begin ===============================================
        if stanza.getName()=='auth':
            session.sasl['next']=['response','abort','auth']
            # client requested some mechanism. May be ever provided credentials already.
            mec=stanza['mechanism']
            session.sasl['mechanism']=mec
            if mec=='PLAIN':
                """The mechanism consists of a single message from the client to the
                   server.  The client sends the authorization identity (identity to
                   login as), followed by a NUL (U+0000) character, followed by the
                   authentication identity (identity whose password will be used),
                   followed by a NUL (U+0000) character, followed by the clear-text
                   password."""
                if session.sasl.has_key('otherdata'): pack=session.sasl['otherdata'].split('\000')
                else: pack=[]
                if len(pack)<>3: res=0
                else:
                    authzid, authcid, passwd = pack
                    res = ( passwd == self._owner.AUTH.getpassword(session.servername, authcid) )
                if res: self.commit_auth(session,authcid)
                else: self.reject_auth(session,authcid)
            elif mec=='DIGEST-MD5': pass
            else:
                session.terminate_stream(Node('failure',{'xmlns':NS_SASL},[Node('invalid-mechanism')]))
            raise NodeProcessed
        elif stanza.getName()=='challenge':
            session.sasl['next']=['challenge','success','failure']
            # DIGEST-MD5 only
            if chal.has_key('qop') and chal['qop']=='auth':
                resp={}
                resp['username']=self.username
                resp['realm']=self._owner.Server
                resp['nonce']=chal['nonce']
                cnonce=''
                for i in range(7):
                    cnonce+=hex(int(random.random()*65536*4096))[2:]
                resp['cnonce']=cnonce
                resp['nc']=('00000001')
                resp['qop']='auth'
                resp['digest-uri']='xmpp/'
                A1=C([H(C([resp['username'],resp['realm'],self.password])),resp['nonce'],resp['cnonce']])
                A2=C(['AUTHENTICATE',resp['digest-uri']])
                response= HH(C([HH(A1),resp['nonce'],resp['nc'],resp['cnonce'],resp['qop'],HH(A2)]))
                resp['response']=response
                resp['charset']='utf-8'
                sasl_data=''
                for key in ['charset','username','realm','nonce','nc','cnonce','digest-uri','response','qop']:
                    if key in ['nc','qop','response','charset']: sasl_data+="%s=%s,"%(key,resp[key])
                    else: sasl_data+='%s="%s",'%(key,resp[key])
                node=Node('response',attrs={'xmlns':NS_SASL},payload=[base64.encodestring(sasl_data[:-1]).replace('\n','')])
                self._owner.send(node.__str__())
            elif chal.has_key('rspauth'): self._owner.send(Node('response',attrs={'xmlns':NS_SASL}).__str__())
        elif stanza.getName()=='response':
            session.sasl['next']=['response','abort']
        elif stanza.getName()=='abort':
            session.sasl['next']=['auth']
        elif stanza.getName()=='success':
            session.sasl['next']=[]
            session.startsasl='success'
            self.DEBUG('Successfully authenticated with remote server.','ok')
            session.StartStream()
        elif stanza.getName()=='failure':
            session.sasl['next']=['challenge','success','failure']
            session.startsasl='failure'
            try: reason=challenge.getChildren()[0]
            except: reason=challenge
            self.DEBUG('Failed SASL authentification: %s'%reason,'error')
        raise NodeProcessed

class Bind(PlugIn):
    def plugin(self,server):
        server.Dispatcher.RegisterHandler('iq',self.bindHandler,typ='set',ns=NS_BIND)
        server.Dispatcher.RegisterHandler('iq',self.sessionHandler,typ='set',ns=NS_SESSION)
        server.feature(NS_BIND)
        server.feature(NS_SESSION)

    def bindHandler(self,session,stanza):
        if session.TYP=='client' or session.__dict__.has_key('resource'):
            session.send(Error(stanza,ERR_SERVICE_UNAVAILABLE))
        else:
            resource=stanza.getTag('bind',namespace=NS_BIND).T.resource.getData()
            if not resource: resource=session.ID
            fulljid="%s@%s/%s"%(session.username,session.servername,resource)
            session.peer=fulljid
            self._owner.deactivatesession(fulljid)
            rep=stanza.buildReply('result')
            rep.T.bind.setNamespace(NS_BIND)
            rep.T.bind.T.jid=fulljid
            session.send(rep)
        raise NodeProcessed

    def sessionHandler(self,session,stanza):
        if session.TYP=='client' or not session.__dict__.has_key('peer') \
          or self._owner.getsession(session.peer)==session:
            session.send(Error(stanza,ERR_SERVICE_UNAVAILABLE))
        else:
            self._owner.activatesession(session)
            session.send(stanza.buildReply('result'))
        raise NodeProcessed
