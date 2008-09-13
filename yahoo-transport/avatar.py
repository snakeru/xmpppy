import httplib,sys,traceback

def getavatar(aid, debug):
    #the aid value is the Avatar ID. This is given in tag 197
    conn = httplib.HTTPConnection("img.msg.yahoo.com")
    if debug: conn.debuglevel=3
    try:
        conn.request("GET","/avatar.php?yids=%s"%aid)
        r1 = conn.getresponse()
    except:
        if debug: traceback.print_exc()
        sys.exc_clear()
        return None
    #print r1.status, r1.reason
    if r1.status == 200:
        try:
            return r1.read()
        except TypeError:
            if debug: traceback.print_exc()
            sys.exc_clear()
            return None
