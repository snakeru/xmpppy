#!/usr/bin/python

import struct

def writefile(path, data):
    type = path[-1][0]
    if type == 0x6d:
        type = 'png'
        data = data[11:]
    elif type in (0x68, 0x6c):
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

class hexer(object):
    def __init__(self,value):
        self.value = value

    def __repr__(self):
        return hex(self.value)

def parse(buffer,path=()):
    entries = []
    offset = 0
    index = 0
    while offset < len(buffer):
        h = struct.unpack_from('!B', buffer, offset)[0]
        l = readdynamicint(buffer, offset + 1)
        d = buffer[offset+l[0]+2:offset+l[0]+l[1]+2]
        if h == 4:
            d = writefile(path, d)
        elif (h >= 0x60 and h <= 0x6F) or (h >= 0xA0 and h <= 0xAF):
            d = parse(d,path+((h,index),))
        entries.append((hexer(h),hexer(l[1]),d))
        offset += l[0] + l[1] + 2
        index += 1
    if offset != len(buffer): raise 'data error: %i != %i' % (offset, len(buffer))
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
