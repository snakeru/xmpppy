import httplib

def getavatar(aid):
    #the aid value is the Avatar ID. This is given in tag 197
    conn = httplib.HTTPConnection("img1.avatar.vip.dcn.yahoo.com")
    conn.request("GET","/users/%s.medium.png"%aid)
    try:
        r1 = conn.getresponse()
    except IOError:
        return None
    #print r1.status, r1.reason
    if r1.status == 200:
        return r1.read()