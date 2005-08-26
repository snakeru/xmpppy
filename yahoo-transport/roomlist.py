import httplib
import re, socket
import htmlutils
YAHOORL="insider.msg.yahoo.com"

def decode_hextoutf8(match):
    	""" This function decodes the hex string into a utf8 return value, or returns '' """
    	#print 'Hex decoder',
    	a = match.group(0)[3:len(match.group(0))-1]
    	if len(a) %2:
    		a = '0'+a
    	try:
    		val = unicode('utf8',a.decode('hex'))
    	except:
    		val = ''
    	#print val
    	return val

def getcata(cata):
    conn = httplib.HTTPConnection(YAHOORL)
    try:
        conn.request("GET","/ycontent/?chatcat=%s"%cata)
    except socket.error:
        return None
    try:
        r1 = conn.getresponse()
    except IOError:
        return None
    #print r1.status, r1.reason
    if r1.status == 200:
        data1 = unicode(r1.read(),'utf-8','replace')
        #print data1
        try:
            t = htmlutils.XHTML2Node(data1)
        except:
            return None
        try:
            cata = t.getChildren()[0].getChildren()
            l = {0:{}}
            for each in cata:
                l[0][each.getAttrs()['id']]=each.getAttrs()['name']
                if each.getChildren() != []:
                    if not l.has_key(each.getAttrs()['id']):
                        l[each.getAttrs()['id']]={}
                    for item in each.getChildren():
                        l[each.getAttrs()['id']][item.getAttrs()['id']]=item.getAttrs()['name']
            #print l
            return l
        except IndexError:
            #print "IndexError"
            return None
    else:
        #print "No get"
        return None

def getrooms(cat):
    #if cat == '0' or cat == 0:
    #   return None
    conn = httplib.HTTPConnection(YAHOORL)
    try:
        conn.request("GET","/ycontent/?chatroom_%s"%(cat))
    except socket.error:
        return None
    try:
        r1 = conn.getresponse()
    except IOError:
        return None
    #print r1.status, r1.reason
    data1 = unicode(r1.read(),'utf-8','replace')
    data1 = re.sub('&#x(d[8-9a-f]..;)|(1.;)','',data1)
    data1 = re.sub('&#x([0-9a-f]*;)',decode_hextoutf8,data1)
    try:
       rooms = htmlutils.XHTML2Node('<?xml version="1.0" encoding="UTF-8" ?>'+data1)
    except:
       open('badxml.xml','w').write('<?xml version="1.0" encoding="UTF-8" ?>'+data1)
       raise
    r = rooms.getChildren()[0].getChildren()
    l = {}
    for each in r:
        a=each.getAttrs()
        p={}
        if a.has_key('name'):
            for item in each.getChildren():
                b = item.getAttrs()
                if b.has_key('count'):
                    p[b['count']]={}
                    if b.has_key('users'):
                        p[b['count']]['users']=b['users']
                    if b.has_key('voices'):
                        p[b['count']]['voices']=b['voices']
                    if b.has_key('webcams'):
                        p[b['count']]['webcams']=b['webcams']
            a['rooms']=p
            #print a
            l[a['name']]=a
    return l

if __name__ == "__main__":
    #print getcata(0)
    print getrooms(1600043463)
    #print getrooms(0)
    
