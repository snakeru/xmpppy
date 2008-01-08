#!/usr/bin/python
# $Id$
version = 'CVS ' + '$Revision$'.split()[1]

import email, os, signal, smtplib, sys, time, traceback, xmpp
from xmpp.browser import *
from email.MIMEText import MIMEText
from email.Header import decode_header
import config, xmlconfig

class Transport:

    online = 1
    restart = 0
    offlinemsg = ''

    def __init__(self,jabber):
        self.jabber = jabber
        self.watchdir = config.watchDir
        if '~' in self.watchdir:
            self.watchdir = self.watchdir.replace('~', os.environ['HOME'])
        # A list of two element lists, 1st is xmpp domain, 2nd is email domain
        self.mappings = [mapping.split('=') for mapping in config.domains]
        email.Charset.add_charset( 'utf-8', email.Charset.SHORTEST, None, None )

    def register_handlers(self):
        self.jabber.RegisterHandler('message',self.xmpp_message)
        self.jabber.RegisterHandler('presence',self.xmpp_presence)
        self.disco = Browser()
        self.disco.PlugIn(self.jabber)
        self.disco.setDiscoHandler(self.xmpp_base_disco,node='',jid=config.jid)

    # Disco Handlers
    def xmpp_base_disco(self, con, event, type):
        fromjid = event.getFrom().__str__()
        to = event.getTo()
        node = event.getQuerynode();
        #Type is either 'info' or 'items'
        if to == config.jid:
            if node == None:
                if type == 'info':
                    return {
                        'ids':[
                            {'category':'gateway','type':'smtp','name':config.discoName}],
                        'features':[NS_VERSION,NS_COMMANDS]}
                if type == 'items':
                    return []
            else:
                self.jabber.send(Error(event,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
        else:
            self.jabber.send(Error(event,MALFORMED_JID))
            raise NodeProcessed

    #XMPP Handlers
    def xmpp_presence(self, con, event):
        # Add ACL support
        fromjid = event.getFrom()
        type = event.getType()
        to = event.getTo()
        if type == 'subscribe':
            self.jabber.send(Presence(to=fromjid, frm = to, typ = 'subscribe'))
        elif type == 'subscribed':
            self.jabber.send(Presence(to=fromjid, frm = to, typ = 'subscribed'))
        elif type == 'unsubscribe':
            self.jabber.send(Presence(to=fromjid, frm = to, typ = 'unsubscribe'))
        elif type == 'unsubscribed':
            self.jabber.send(Presence(to=fromjid, frm = to, typ = 'unsubscribed'))
        elif type == 'probe':
            self.jabber.send(Presence(to=fromjid, frm = to))
        elif type == 'unavailable':
            self.jabber.send(Presence(to=fromjid, frm = to, typ = 'unavailable'))
        elif type == 'error':
            return
        else:
            self.jabber.send(Presence(to=fromjid, frm = to))

    def xmpp_message(self, con, event):
        type = event.getType()
        fromjid = event.getFrom()
        fromstripped = fromjid.getStripped()
        to = event.getTo()
        try:
            if event.getSubject.strip() == '':
                event.setSubject(None)
        except AttributeError:
            pass
        if event.getBody() == None:
            return
        if to.getNode() != '':

            mto = to.getNode().replace('%', '@')

            fromsplit = fromstripped.split('@', 1)
            mfrom = None
            for mapping in self.mappings:
                if mapping[0] == fromsplit[1]:
                    mfrom = '%s@%s' % (fromsplit[0], mapping[1])

            if mfrom:
                subject = event.getSubject()
                body = event.getBody()

                charset = 'utf-8'
                body = body.encode(charset, 'replace')

                msg = MIMEText(body, 'plain', charset)
                if subject: msg['Subject'] = subject
                msg['From'] = mfrom
                msg['To'] = mto

                try:
                    if config.dumpProtocol: print 'SENDING:\n' + msg.as_string()
                    mailserver = smtplib.SMTP(config.smtpServer)
                    if config.dumpProtocol: mailserver.set_debuglevel(1)
                    mailserver.sendmail(mfrom, mto, msg.as_string())
                    mailserver.quit()
                except:
                    logError()
                    self.jabber.send(Error(event,ERR_RECIPIENT_UNAVAILABLE))

            else:
                self.jabber.send(Error(event,ERR_REGISTRATION_REQUIRED))
        else:
            self.jabber.send(Error(event,ERR_ITEM_NOT_FOUND))

    def mail_check(self):

        if time.time() < self.lastcheck + 5:
            return

        self.lastcheck = time.time()

        mails = os.listdir(self.watchdir)

        for mail in mails:
            fullname = '%s%s' % (self.watchdir, mail)
            fp = open(fullname)
            msg = email.message_from_file(fp)
            fp.close()
            os.remove(fullname)

            if config.dumpProtocol: print 'RECEIVING:\n' + msg.as_string()

            mfrom = email.Utils.parseaddr(msg['From'])[1]
            mto = email.Utils.parseaddr(msg['To'])[1]

            jfrom = '%s@%s' % (mfrom.replace('@', '%'), config.jid)

            tosplit = mto.split('@', 1)
            jto = None
            for mapping in self.mappings:
                if mapping[1] == tosplit[1]:
                    jto = '%s@%s' % (tosplit [0], mapping[0])

            if not jto: continue

            (subject, charset) = decode_header(msg['Subject'])[0]
            if charset: subject = unicode(subject, charset, 'replace')

            # we are assuming that text/plain will be first
            while msg.is_multipart():
                msg = msg.get_payload(0)
                if not msg: continue

            charset = msg.get_charsets('us-ascii')[0]
            body = msg.get_payload(None,True)
            body = unicode(body, charset, 'replace')

            m = Message(to=jto,frm = jfrom, subject = subject, body = body)
            self.jabber.send(m)

    def xmpp_connect(self):
        connected = self.jabber.connect((config.mainServer,config.port))
        if config.dumpProtocol: print "connected:",connected
        while not connected:
            time.sleep(5)
            connected = self.jabber.connect((config.mainServer,config.port))
            if config.dumpProtocol: print "connected:",connected
        self.register_handlers()
        if config.dumpProtocol: print "trying auth"
        connected = self.jabber.auth(config.saslUsername,config.secret)
        if config.dumpProtocol: print "auth return:",connected
        return connected

    def xmpp_disconnect(self):
        time.sleep(5)
        if not self.jabber.reconnectAndReauth():
            time.sleep(5)
            self.xmpp_connect()

def loadConfig():
    configOptions = {}
    for configFile in config.configFiles:
        if os.path.isfile(configFile):
            xmlconfig.reloadConfig(configFile, configOptions)
            config.configFile = configFile
            return
    print "Configuration file not found. You need to create a config file and put it in one of these locations:\n    " + "\n    ".join(config.configFiles)
    sys.exit(1)

def logError():
    err = '%s - %s\n'%(time.strftime('%a %d %b %Y %H:%M:%S'),version)
    if logfile != None:
        logfile.write(err)
        traceback.print_exc(file=logfile)
        logfile.flush()
    sys.stderr.write(err)
    traceback.print_exc()
    sys.exc_clear()

def sigHandler(signum, frame):
    transport.offlinemsg = 'Signal handler called with signal %s'%signum
    if config.dumpProtocol: print 'Signal handler called with signal %s'%signum
    transport.online = 0

if __name__ == '__main__':
    if 'PID' in os.environ:
        config.pid = os.environ['PID']
    loadConfig()
    if config.pid:
        pidfile = open(config.pid,'w')
        pidfile.write(`os.getpid()`)
        pidfile.close()

    if config.saslUsername:
        sasl = 1
    else:
        config.saslUsername = config.jid
        sasl = 0

    logfile = None
    if config.debugFile:
        logfile = open(config.debugFile,'a')

    if config.dumpProtocol:
        debug=['always', 'nodebuilder']
    else:
        debug=[]
    connection = xmpp.client.Component(config.jid,config.port,debug=debug,sasl=sasl,bind=config.useComponentBinding,route=config.useRouteWrap)
    transport = Transport(connection)
    if not transport.xmpp_connect():
        print "Could not connect to server, or password mismatch!"
        sys.exit(1)
    # Set the signal handlers
    signal.signal(signal.SIGINT, sigHandler)
    signal.signal(signal.SIGTERM, sigHandler)
    transport.lastcheck = time.time() + 10
    while transport.online:
        try:
            connection.Process(1)
            transport.mail_check()
        except KeyboardInterrupt:
            _pendingException = sys.exc_info()
            raise _pendingException[0], _pendingException[1], _pendingException[2]
        except IOError:
            transport.xmpp_disconnect()
        except:
            logError()
        if not connection.isConnected():  transport.xmpp_disconnect()
    connection.disconnect()
    if config.pid:
        os.unlink(config.pid)
    if logfile:
        logfile.close()
    if transport.restart:
        args=[sys.executable]+sys.argv
        if os.name == 'nt': args = ["\"%s\"" % a for a in args]
        if config.dumpProtocol: print sys.executable, args
        os.execv(sys.executable, args)
