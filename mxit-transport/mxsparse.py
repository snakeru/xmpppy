#!/usr/bin/python

import struct

def writefile(path, data):
    type = path[-1][0]
    if type in (0x68, 0x6c, 0x6d):
        type = 'png'
    elif type == 0x6e:
        type = 'mid'
    else:
        type = hex(type)[2:]
    filename = 'mxs-' + '-'.join(('.'.join((str(y) for y in x)) for x in path)) + '.' + type
    f = open(filename, 'wb')
    f.truncate()
    f.write(data)
    f.close()
    return filename

def readdynamicint(buffer, offset):
    type = struct.unpack_from('!B', buffer, offset)[0]
    if type < 0x80:
        return (0,type)
    elif type == 0x81:
        return (1,) + struct.unpack_from('!B', buffer, offset + 1)
    elif type == 0x82:
        return (2,) + struct.unpack_from('!H', buffer, offset + 1)
    else:
        raise 'failed to read dynamicint:%i,%s' % (type,`buffer[offset:offset+20]`)

class formatter(object):
    def __init__(self,value,format):
        self.repr = format%value

    def __repr__(self):
        return self.repr

def parsesplash(buffer):
    entries = []
    offset = 0
    while offset < len(buffer):
        h = struct.unpack_from('!B', buffer, offset)[0]
        offset += 1
        if h == 0:
            break
        l = struct.unpack_from('!I', buffer, offset)[0]
        entries.append((formatter(h,'0x%02x'),formatter(l,'0x%08x')))
        offset += 4
    return entries, buffer[offset:]

def parse(buffer,path=()):
    entries = []
    offset = 0
    index = 0
    while offset < len(buffer):
        h = struct.unpack_from('!B', buffer, offset)[0]
        e, l = readdynamicint(buffer, offset + 1)
        offset += 2 + e
        d = buffer[offset:offset + l]
        offset += l
        if h == 4:
            if path[-1][0] == 0x6d:
                i, d = parsesplash(d)
                d = i + [writefile(path, d),]
            else:
                d = writefile(path, d)
        elif (h >= 0x60 and h <= 0x6F) or (h >= 0xA0 and h <= 0xAF):
            d = parse(d,path+((h,index),))
        entries.append((formatter(h,'0x%02x'),formatter(l,'0x%04x' if l > 0xff else '0x%02x'),d))
        index += 1
        if len(path) != 0: continue
        if len(buffer) - offset < 4: break
        c = struct.unpack_from('!I', buffer, offset)[0]
        entries.append(formatter(c,'0x%08x'))
        offset += 4
        break
    if offset < len(buffer): raise 'data left over: %i bytes: %s' % (len(buffer) - offset, `buffer[offset:]`)
    if offset > len(buffer): raise 'ran out of data: %i bytes needed' % (offset - len(buffer))
    return entries

def loadskin(filename):
    f = open(filename,'rb')
    skin = (f.read(4),parse(f.read()))
    f.close()
    return skin

if __name__ == '__main__':
    import sys
    from pprint import pprint
    for each in sys.argv[1:]:
        skin = loadskin(each)
        pprint(skin, width=120)
