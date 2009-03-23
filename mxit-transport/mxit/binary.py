import struct

class BinaryStream:
    def __init__(self, con, data=''):
        self.data = data
        self.con = con
        
        
    def _read_bin(self, fmt):
        l = struct.calcsize('!' + fmt)
        r = struct.unpack('!' + fmt, self.data[:l])
        self.data = self.data[l:]
        return r
    
    def read(self, fmt):
        """ Read binary data from a stream.
        
        fmt is a format string, consisting of the following characters:
        B - unsigned byte (1 byte)
        H - unsigned short (2 bytes)
        I - unsigned int (4 bytes)
        Q - unsigned long (8 bytes)
        S - string (2 bytes indicating the length of a string, followed by the string)
        
        The data is returned in a list.
        """
        
        result = []
        while True:
            i = fmt.find('S')
            if i >= 0:
                r = self._read_bin(fmt[:i])
                result += r
                r = self._read_bin('H')
                sl = r[0]
                s, = self._read_bin('%ds' % sl)
                if self.con:
                    s = self.con.from_mxit(s)
                result.append(s)
                fmt = fmt[i+1:]
            else:
                r = self._read_bin(fmt)
                result += r
                break
        return result
    
    def read_bytes(self, n):
        r = self.data[:n]
        self.data = self.data[n:]
        return r
    
    def __len__(self):
        return len(self.data)
    
    def write_bytes(self, bytes):
        self.data += bytes
        
    def _write_bin(self, fmt, data):
        n = len(filter(lambda c: c.isalpha(), fmt))
        self.data += struct.pack('!' + fmt, *data[:n])
        data = data[n:]
        return data
        
    def write(self, fmt, *data):
        """ Write binary data to a stream.
        
        fmt is a format string, consisting of the following characters:
        B - unsigned byte (1 byte)
        H - unsigned short (2 bytes)
        I - unsigned int (4 bytes)
        Q - unsigned long (8 bytes)
        S - string (2 bytes indicating the length of a string, followed by the string)
        """
        
        while True:
            i = fmt.find('S')
            if i >= 0:
                data = self._write_bin(fmt[:i], data)
                if self.con:
                    s = self.con.to_mxit(data[0])
                else:
                    s = str(data[0])
                l = len(s)
                self._write_bin('H%ds' % l, (l, s))
                data = data[1:]
                fmt = fmt[i+1:]
            else:
                data = self._write_bin(fmt, data)
                break
        return data