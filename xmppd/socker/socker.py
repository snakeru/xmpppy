#!python
# -*- coding: UTF-8 -*-
# 
# Socker™ network load balancer & reverse proxy dæmon
#
# Copyright (C) 2005 BlueBridge Technologies Group, Inc.
# All rights reserved.
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
# 
# [*] Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
# 
# [*] Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
# 
# [*] Neither the name of BlueBridge Technologies nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.

"Socker™ network load balancer & reverse proxy dæmon"

__author__    = "Kristopher Tate <kris@bbridgetech.com>"
__version__   = "0.2"
__copyright__ = "Copyright (C) 2005 BlueBridge Technologies Group, Inc."
__license__   = "BSD"

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-t", "--test",
                action="store_true", dest="enable_test",
                help="Start-up test configuration")

(cmd_options, cmd_args) = parser.parse_args()

import socket, time, threading, thread, event, sys, xmlrpclib, traceback

# maximum allowed length of XML-RPC request (in bytes)
MAXREQUESTLENGTH = 10000
XMLRPC_PORT = 8000

class Client:
    def __init__(self,socket,owner,type_guid,server_guid,fsock=False):
        self._sock = socket
        self._owner = owner
        self._tguid = type_guid
        self._sguid = server_guid
        self.linked = False
        
        if fsock == False: self.connect(type_guid,server_guid)
        
    def connect(self,type_guid,server_guid):
        #create an INET, STREAMing socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #Now connect
        destination = (self._owner.routes[type_guid][server_guid]['info']['host'], self._owner.routes[type_guid][server_guid]['info']['port'])
        print("connecting to ", destination)
        sock.connect(destination)

        s = Client(sock,self._owner,type_guid,server_guid,True)

        self._owner.registersession(s,2,type_guid,server_guid)
        self._owner.link_manager('a',self,s)

        s.linked = True
        self.linked = True

        return s
        
    def route(self,data,fileno):
        s = self._owner.sockets[self._owner.links[fileno]['fn']]['sock']
        s.send(data)

    def receive(self):
        """Reads all pending incoming data. Raises IOError on disconnect."""
        try: received = self._sock.recv(40960)
        except: received = ''

        if len(received) == 0: # length of 0 means disconnect
            raise IOError("Peer disconnected")
        return received

    def send(self,msg):
        try:
            totalsent = 0
            while totalsent < len(msg):
                sent = self._sock.send(msg[totalsent:])
                if sent == 0:
                    self.terminate()
                totalsent = totalsent + sent
        except:
            pass
    
    def fileno(self): return self._sock.fileno()
    def getsockname(self): return self._sock.getsockname()
    
    def terminate(self):
        if self.linked == True:
            linkup = self._owner.sockets[self._owner.links[self.fileno()]['fn']]['sock']
                        
            print("Terminating %s::%s"%(self.fileno(),linkup.fileno()))
            self._owner.link_manager('r',self)
            self._owner.unregistersession(linkup)
            # Handle forward socket
            linkup._sock.close()

        # Handle our socket
        self._owner.unregistersession(self)
        self._sock.close()
        
        self.linked = False
        
        
          
class Router:

    def __init__(self):
        self.leventobjs={}
        self.sockets={}
        self.types_by_port={}
        self.socket_by_port={}
        self.links = {}
        self.routes={}
        self.SESS_LOCK=thread.allocate_lock()
        self.port_pool = []
#        self.register_port(2005)
        self.register_xmlrpc_agent()

    def register_xmlrpc_agent(self):
        self.SESS_LOCK.acquire()
        
        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', globals()['XMLRPC_PORT'])) #add host_name specific later
        s.listen(1)

        self.sockets[s.fileno()] = {'sock':s,'special':'XMLRPC'} #Register socket
                
        self.leventobjs[s.fileno()]= event.event(self.libevent_read_callback, handle = s, evtype = event.EV_TIMEOUT | event.EV_READ | event.EV_PERSIST) #Register callback agent
        if self.leventobjs[s.fileno()] != None:
            self.leventobjs[s.fileno()].add() #Add agent to the queue.
            
        self.SESS_LOCK.release()
        print("XMLRPC has been registered to port %i"%globals()['XMLRPC_PORT'])
        return True

    def register_port(self,outside_port,type_guid,server_guid,server_host,server_port,options=None):  
        "Takes a port number, binds it to the server, registers it into the registry, and then returns the socket handle"     
        if outside_port not in self.port_pool:
            s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', outside_port)) #add host_name specific later
            s.listen(1)
            
            self.port_pool += [outside_port]
            print("We have registered port No. %i"%outside_port)
            r = self.registersession(s,1,type_guid,server_guid,server_host,server_port,options)
            return {'mode':1,'s':r}
        else:
            r = self.registersession(None,3,type_guid,server_guid,server_host,server_port,options)
            return {'mode':3,'s':r}

    def link_manager(self,mode,client,server=None):
        try:
            if mode == 'a' and server != None:
                self.links[client.fileno()] = {'fn':server.fileno(),'typ':'server'}
                self.links[server.fileno()] = {'fn':client.fileno(),'typ':'client'}
                print("Link up between %s and %s"%(client.fileno(),server.fileno()))
            elif mode == 'r':
                other = self.links[client.fileno()]['fn']
                del self.links[client.fileno()]
                del self.links[other]
                print("Link down between %s and %s"%(client.fileno(),other))
        except:
            pass
            
    def registersession(self,s,mode,type_guid,server_guid,server_host=None,server_port=None,options=None):          
        self.SESS_LOCK.acquire()
        
        if mode == 0:
            self.routes[type_guid][server_guid]['clients'] += [s]
        elif mode == 1 or mode == 3:
            if self.routes.has_key(type_guid) == False: self.routes[type_guid] = {}
            if mode == 1: self.routes[type_guid]['bind'] = s
            if self.routes[type_guid].has_key(server_guid) == False:
                self.routes[type_guid].update({server_guid:{'clients':[],
                                                            'info':{'port':server_port,
                                                                    'host':server_host},
                                                            'channels':[]}})
            else:
                self.routes[type_guid][server_guid]['info'] = {'port':server_port,'host':server_host,'bind':s}
            if type(options) == type({}):
                for x,y in options.iteritems():
                    self.routes[type_guid][server_guid]['info'][x] = y
            
            if mode == 3:
                self.SESS_LOCK.release()
                print("registered secondary as type %s" % str(mode))
                return s
            else:
                self.types_by_port[str(s.getsockname()[1])] = type_guid

        elif mode == 2:
            self.routes[type_guid][server_guid]['channels'] += [s]
        
        self.sockets[s.fileno()] = {'sock':s,'tguid':type_guid,'sguid':server_guid} #Register socket
                
        self.leventobjs[s.fileno()]= event.event(self.libevent_read_callback, handle = s, evtype = event.EV_TIMEOUT | event.EV_READ | event.EV_PERSIST) #Register callback agent
        if self.leventobjs[s.fileno()] != None:
            self.leventobjs[s.fileno()].add() #Add agent to the queue.
        self.SESS_LOCK.release()
        print("registered socket %s as type %s" % (s.fileno(),str(mode)))
        return s

    def unregistersession(self,s=None,type_guid=None,server_guid=None):          
        if s != None and s != 0:
            if type(s) == type(1):
                try:
                    s = self.sockets[s]['sock']
                except:
                    return False            

#        print('keys!!!!',len(self.routes[type_guid].keys()), self.routes[type_guid].keys())
        if type_guid != None and len(self.routes[type_guid].keys()) <= 2:
            s = self.routes[type_guid]['bind']
            self.unregister_port(s)
    
            if self.leventobjs.has_key(s.fileno()) == True and self.leventobjs[s.fileno()] != None:
                self.leventobjs[s.fileno()].delete() # Kill libevent event
                del self.leventobjs[s.fileno()]
                
            del self.sockets[s.fileno()] # Destroy the record
            del self.routes[type_guid]
            
            s.close() # close our server watching guy!    

        try:
            if type_guid == None or server_guid == None and s != None and s != 0:
                self.routes[self.sockets[s.fileno()]['tguid']][self.sockets[s.fileno()]['sguid']]['clients'].remove(s)
                self.routes[self.sockets[s.fileno()]['tguid']][self.sockets[s.fileno()]['sguid']]['channels'].remove(s)
            elif type_guid != None and server_guid != None:  
                del self.routes[type_guid][server_guid]
        except:
            pass

        if type_guid == None or server_guid == None and s != None and s != 0:
            if self.leventobjs.has_key(s.fileno()) == True and self.leventobjs[s.fileno()] != None:
                self.leventobjs[s.fileno()].delete() # Kill libevent event
                del self.leventobjs[s.fileno()]
            del self.sockets[s.fileno()] # Destroy the record
            print("UNregistered socket %s"%s.fileno())
        else:
            print("UNregistered socket %s::%s"%(type_guid,server_guid))
        return True

    def unregister_port(self,s):
        if type(s) == type(1):
            try:
                s = self.sockets[s]['sock']
            except:
                return False
        try:
            port = s.getsockname()[1]
            self.port_pool.remove(port)
            del self.types_by_port[str(port)]
            print("UNREGISTERED PORT %i"%port)
            return True
        except:
            return False
                    
    def libevent_read_callback(self, ev, fd, evtype, pipe):
        if isinstance(fd,Client):
            sess=fd
            try:
                data=sess.receive()
            except IOError: # client closed the connection
                sess.terminate()
                data=''
            if data:
                sess.route(data,fd.fileno())
        elif isinstance(fd,socket.socket):
            conn, addr = fd.accept()
            host,port=fd.getsockname()
            if port in self.port_pool:
                type_guid = self.types_by_port[str(port)]
                server = self.get_good_server(type_guid)
                if server != None:               
                    print("Using server %s"%server)
                    sess = Client(conn,self,type_guid,server)
                    self.registersession(sess,0,self.types_by_port[str(port)],server)
            elif port == globals()['XMLRPC_PORT']:
                try:
                    conn.recv(globals()['MAXREQUESTLENGTH']) #Get client's headers out of the buffer
                    conn.send('') #let it know that we're ready to accept
                    data = conn.recv(globals()['MAXREQUESTLENGTH'])
                    contentLength = len(data)
                    if contentLength > MAXREQUESTLENGTH:
                        raise Exception, 'Request too large'
        
                    params, method = xmlrpclib.loads(data)
                    if type(params[0]) == type({}): 
                        aside = params[0]
                        aside['_socket'] = conn
                        aside['_socket_info'] = (host,port)
                        params = (aside,)
                    result = self.rpc_dispatch(method, params)
                    if getattr(result,'faultCode',None) != None:
                        response = xmlrpclib.dumps(result)            
                    else:
                        print(result)
                        response = xmlrpclib.dumps(result, methodresponse=1)
        
                except:
                    response = xmlrpclib.dumps(xmlrpclib.Fault(1, "Socker(tm): %s"%traceback.format_exc()))

                final_output = ["HTTP/1.1 200 OK","Server: BlueBridge Socker(tm)","Content-Length: %i"%len(response),"Connection: close","Content-Type: text/xml","",response]
                                
                conn.send('\n'.join(final_output))
                conn.close()

        else: raise "Unknown instance type: %s"%sock

    def get_good_server(self,type_guid):
        out = None
        for server,info in self.routes[type_guid].iteritems():
            if server == 'bind': continue
            if info['info'].has_key('conn_max') == False:
                info['info']['conn_max'] = 1000 # Change all of this later
            print("Info:", server, len(info['clients']), info['info']['conn_max'])
            if len(info['clients']) < info['info']['conn_max']:
                out = server
                break
        return out
        
    """def shutdown(self,reason):
        global GLOBAL_TERMINATE
        GLOBAL_TERMINATE = True
        socklist=self.sockets.keys()
        for fileno in socklist:
            s=self.sockets[fileno]
            if isinstance(s,socket.socket):
                self.unregistersession(s)
                s.shutdown(2)
                s.close()
            elif isinstance(s,Client): s.terminate_stream(reason)"""


    def rpc_dispatch(self, method, params):
        try:
            # We are forcing the 'export_' prefix on methods that are
            # callable through XML-RPC to prevent potential security
            # problems
            func = getattr(self, 'export_' + method)
        except AttributeError:
            raise Exception('method "%s" is not supported' % method)
        else:
            result = func(*params)
            if getattr(result,'faultCode',None) == None:
                result = (result,)
            return result

    def execute_program (self, command):
        import os
        a = os.popen(command,'r')
        out = str(a.read()).replace("\n", "")
        a.close()
        return out

    def export_hello(self,inpt):
        return {'code':1,'msg':'Server is online!'}

    def export_hostname(self,inpt):
        print(inpt)
        if inpt.has_key('_socket_info'):
            return {'code':1,'hostname':inpt['_socket_info'][0]}
        else:
            return {'code':0,'msg':'Cannot detect your hostname!'}

    def export_uuidgen(self,args):
        uuid = self.execute_program('uuidgen') #Look for uuidgen for super-fast uuid generation.
        if len(uuid) > 0:        
            import re,sha
            y = re.compile('^(.*)-(.*)-(.*)-(.*)-(.*)$')
            r = y.match('6aa6cd92-1b15-4ccd-98a0-7a77b473fe4b').group(0,1,2,3,4,5)
            return '{%s%s-%s-%s-%s}' % (r[1],r[2],r[3],r[4],sha.new(str(time.time())).hexdigest()[20:])

        else:
            import random, md5
            t = long( time.time() * 1000 )
            r = long( random.random()*100000000000000000L )
            try:
                a = socket.gethostbyname( socket.gethostname() )
            except:
                # if we can't get a network address, just imagine one
                a = random.random()*100000000000000000L
            data = str(t)+' '+str(r)+' '+str(a)+' '+str(args)
            data = md5.md5(data).hexdigest()
            return '{%s}' % data

    def export_add(self, inpt):
        try:
            options = None
            if inpt.has_key('conn_max'):
                options = {'conn_max':inpt['conn_max']}

            if inpt['outside_port'] == globals()['XMLRPC_PORT']:
                s = None
            else:
                s = self.register_port(inpt['outside_port'],inpt['type_guid'],inpt['server_guid'],inpt['server_host'],inpt['server_port'],options)
            
            if s['s'] == None and s['mode'] == 3:
                return {'code':1,'status':'registered','handle':0,'mode':s['mode'],'port':inpt['server_port'],'outside_port':inpt['outside_port']}
            elif s['s']:
                return {'code':1,'status':'registered','handle':s['s'].fileno(),'mode':s['mode'],'port':inpt['server_port'],'outside_port':inpt['outside_port']}
            else:
                return {'code':0,'status':'unknown error'}
        except:
            return xmlrpclib.Fault(1, "Datastar RPC (%s): %s" % sys.exc_info()[:2])
            
    def export_delete(self,inpt):
        try:
            result = self.unregistersession(inpt['handle'],inpt['type_guid'],inpt['server_guid'])
            if result == True:
                return {'code':1,'status':'unregistered'}
            else:
                return {'code':0,'status':'unknown error'}        
        except:
            return xmlrpclib.Fault(1, "Datastar RPC: %s" % traceback.format_exc())

def _lib_out():
    event.abort()

r = Router()

if cmd_options.enable_test == True:
    options = {'conn_max':300}
    options2 = {'conn_max':300}
    
    inpt = {'outside_port':9000,'type_guid':'apple','server_guid':'co_jp','server_host':'www.apple.co.jp','server_port':80}
    inpt2 = {'outside_port':9000,'type_guid':'apple','server_guid':'com','server_host':'www.apple.com','server_port':80}
    
    r.register_port(inpt['outside_port'],inpt['type_guid'],inpt['server_guid'],inpt['server_host'],inpt['server_port'],options)
    r.register_port(inpt2['outside_port'],inpt2['type_guid'],inpt2['server_guid'],inpt2['server_host'],inpt2['server_port'],options2)

event.signal(2,_lib_out).add()          
#Server(r).start()
event.dispatch()