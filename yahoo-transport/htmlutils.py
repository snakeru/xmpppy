#!/usr/bin/env python

from xmpp.simplexml import Node,T,NT,ustr, XMLescape
import HTMLParser

ENCODING='utf8'
DBG_NODEBUILDER = 'nodebuilder'
class NodeBuilder:
    """ Builds a Node class minidom from data parsed to it. This class used for two purposes:
        1. Creation an XML Node from a textual representation. F.e. reading a config file. See an XML2Node method.
        2. Handling an incoming XML stream. This is done by mangling 
           the __dispatch_depth parameter and redefining the dispatch method.
        You do not need to use this class directly if you do not designing your own XML handler."""
    def __init__(self,data=None,initial_node=None):
        """ Takes two optional parameters: "data" and "initial_node".
            By default class initialised with empty Node class instance.
            Though, if "initial_node" is provided it used as "starting point".
            You can think about it as of "node upgrade".
            "data" (if provided) feeded to parser immidiatedly after instance init.
            """
        self.DEBUG(DBG_NODEBUILDER, "Preparing to handle incoming XML stream.", 'start')
        self._parser = HTMLParser.HTMLParser()
        self._parser.handle_starttag       = self.starttag
        self._parser.handle_endtag         = self.endtag
        self._parser.handle_data      = self.handle_data
        self._parser.handle_charref = self.handle_charref
        #self._parser.StartNamespaceDeclHandler = self.handle_namespace_start
        self.Parse = self._parser.feed

        self.__depth = 0
        self._dispatch_depth = 1
        self._document_attrs = None
        self._mini_dom=initial_node
        self.last_is_data = 1
        self._ptr=None
        self.namespaces={"http://www.w3.org/XML/1998/namespace":'xml:'}
        self.xmlns="http://www.w3.org/XML/1998/namespace"

        if data: 
        	self._parser.feed(data)
        	self._parser.close()

    def destroy(self):
        """ Method used to allow class instance to be garbage-collected. """
        self._parser.StartElementHandler       = None
        self._parser.EndElementHandler         = None
        self._parser.CharacterDataHandler      = None
        self._parser.StartNamespaceDeclHandler = None

    def starttag(self, tag, attr):
        """XML Parser callback. Used internally"""
        attrs={}
        #attlist=attrs.keys()       #
        #for attr in attlist:       # FIXME: Crude hack. And it also slows down the whole library considerably.
        #    sp=attr.rfind(" ")     #
        #    if sp==-1: continue    #
        #    ns=attr[:sp]           #
        #    attrs[self.namespaces[ns]+attr[sp+1:]]=attrs[attr]
        #    del attrs[attr]        #
        for each in attr:
        	attrs[each[0]]=each[1]
        self.__depth += 1
        self.DEBUG(DBG_NODEBUILDER, "DEPTH -> %i , tag -> %s, attrs -> %s" % (self.__depth, tag, `attrs`), 'down')
        if self.__depth == self._dispatch_depth:
            if not self._mini_dom : self._mini_dom = Node(tag=tag, attrs=attrs)
            else: Node.__init__(self._mini_dom,tag=tag, attrs=attrs)
            self._ptr = self._mini_dom
        elif self.__depth > self._dispatch_depth:
            self._ptr.kids.append(Node(tag=tag,parent=self._ptr,attrs=attrs))
            self._ptr = self._ptr.kids[-1]
        if self.__depth == 1:
            self._document_attrs = attrs
            ns, name = (['']+tag.split())[-2:]
            self.stream_header_received(ns, name, attrs)
        if not self.last_is_data and self._ptr.parent: self._ptr.parent.data.append('')
        self.last_is_data = 0

    def endtag(self, tag ):
        """XML Parser callback. Used internally"""
        self.DEBUG(DBG_NODEBUILDER, "DEPTH -> %i , tag -> %s" % (self.__depth, tag), 'up')
        if self.__depth == self._dispatch_depth:
            self.dispatch(self._mini_dom)
        elif self.__depth > self._dispatch_depth:
            self._ptr = self._ptr.parent
        else:
            self.DEBUG(DBG_NODEBUILDER, "Got higher than dispatch level. Stream terminated?", 'stop')
        self.__depth -= 1
        self.last_is_data = 0
        if self.__depth == 0: self.stream_footer_received()

    def handle_data(self, data):
        """XML Parser callback. Used internally"""
        self.DEBUG(DBG_NODEBUILDER, data, 'data')
        if not self._ptr: return
        if self.last_is_data:
            self._ptr.data[-1] += data
        else:
            self._ptr.data.append(data)
            self.last_is_data = 1

    def handle_charref(self,data):
    	print "Got chardata: ", data

    def handle_namespace_start(self, prefix, uri):
        """XML Parser callback. Used internally"""
        if prefix: self.namespaces[uri]=prefix+':'
        else: self.xmlns=uri
    def DEBUG(self, level, text, comment=None):
        """ Gets all NodeBuilder walking events. Can be used for debugging if redefined."""
    def getDom(self):
        """ Returns just built Node. """
        return self._mini_dom
    def dispatch(self,stanza):
        """ Gets called when the NodeBuilder reaches some level of depth on it's way up with the built
            node as argument. Can be redefined to convert incoming XML stanzas to program events. """
    def stream_header_received(self,ns,tag,attrs):
        """ Method called when stream just opened. """
    def stream_footer_received(self):
        """ Method called when stream just closed. """

def XHTML2Node(xml):
	return NodeBuilder(xml).getDom()
