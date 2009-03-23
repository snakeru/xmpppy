from mxit.binary import BinaryStream
from mxit.errors import *
from mxit.encryption import decrypt

def read_mxm(data, password=None):
    if not data.startswith('MXM'):
        raise MxitException('Not an MXM file')
    
    stream = BinaryStream(None, data[3:])
    type, = stream.read('B')
    if type == 2:
        pass
    elif type == 6:
        if password:
            text = decrypt(password, stream.data)
            stream = BinaryStream(None, text)
        else:
            raise MxitException('Encrypted file, password required')
    else:
        raise MxitException('Unknown MXM file type')
    stream.read('I')    #should equal 4
    n, = stream.read('I')    # number of messages

    for i in range(n):
        a, b, sender, to, message, c = stream.read('IQSSSI')
        print "%s: %s" % (sender, message)
    
    