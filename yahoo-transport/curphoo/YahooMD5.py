# YahooMD5.py
#
# gaim
#
# Some code copyright (C) 1998-1999, Mark Spencer <markster@marko.net>
# libfaim code copyright 1998, 1999 Adam Fritzler <afritz@auk.cx>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#

# Python port for the curphoo/xmpp.py project
#   by Norman Rasmussen <norman@rasmussen.co.za>

# The curphoo_process_auth code comes from the GAIM project.

import md5
import pysha
from string import maketrans
from yahoo_fn import yahoo_xfrm
from md5crypt import md5crypt

base64translate = maketrans('+/=', '._-')

alphabet1 = 'FBZDWAGHrJTLMNOPpRSKUVEXYChImkwQ'
alphabet2 = 'F0E1D2C3B4A59687abcdefghijklmnop'

challenge_lookup    = 'qzec2tb3um1olpar8whx4dfgijknsvy5'
operand_lookup      = '+|&%/*^-'
delimit_lookup      = ',;'

def curphoo_process_auth(username, password, seed):

    # 
    # Magic: Phase 1.  Generate what seems to be a 30 
    # byte value (could change if base64
    # ends up differently?  I don't remember and I'm 
    # tired, so use a 64 byte buffer.
    #

    magic1 = ''
    for char in seed:
        if char == '(' or char == ')': continue
        if char.isalpha() or char.isdigit():
            magic_work = challenge_lookup.index(char) << 3
        else:
            local_store = operand_lookup.index(char)
            magic1 += chr(magic_work | local_store)
            
    # Magic: Phase 2.  Take generated magic value and 
    # sprinkle fairy dust on the values.

    magic2 = ''
    for c in range(len(magic1)-1,0,-1):
        byte1 = ord(magic1[c-1])
        byte2 = ord(magic1[c])
        
        byte1 *= 0xcd
        byte1 &= 0xff
        byte1 ^= byte2
        
        magic2 = chr(byte1) + magic2

    magic2 = magic1[0] + magic2

    # Magic: Phase 3.  This computes 20 bytes.  The first 4 bytes are used as our magic 
    # key (and may be changed later); the next 16 bytes are an MD5 sum of the magic key 
    # plus 3 bytes.  The 3 bytes are found by looping, and they represent the offsets 
    # into particular functions we'll later call to potentially alter the magic key. 

    cnt = 1
    comparison_src = ''
    while cnt < len(magic2) and len(comparison_src) < 20:
        bl = 0
        cl = ord(magic2[cnt])
        cnt = cnt + 1

        if cl > 0x7f:
            if cl < 0xe0:
                bl = cl = (cl & 0x1f) << 6
            else:
                bl = ord(magic2[cnt])
                cnt = cnt + 1
                cl = (cl & 0x0f) << 6
                bl = ((bl & 0x3f) + cl) << 6
            cl = ord(magic2[cnt])
            cnt = cnt + 1
            bl = (cl & 0x3f) + bl
        else:
            bl = cl

        comparison_src += chr((bl & 0xff00) >> 8) + chr(bl & 0xff)

    # Compute values for recursive function table!
    try:
        for i in range(0xffff):
            for j in range(5):
                chal = comparison_src[:4] + chr(i & 0xff) + chr(i >> 8) + chr(j)
                result = md5.new(chal).digest()
                if result == comparison_src[4:]: 
                    depth = i
                    table = j
                    raise 'done'
    except 'done':
        pass  

    x = ord(comparison_src[3]) << 24l | ord(comparison_src[2]) << 16 | ord(comparison_src[1]) << 8 | ord(comparison_src[0])
    x = yahoo_xfrm( table, depth, x )
    x = yahoo_xfrm( table, depth, x )
    magic_key_char = chr(x & 0xFF) + chr(x >> 8 & 0xFF) + chr(x >> 16 & 0xFF) + chr(x >> 24 & 0xFF)

    crypt_result = md5crypt(password, '_2S43d5f')

    return [
        finalstep(password,     magic_key_char, table), 
        finalstep(crypt_result, magic_key_char, table)]

def finalxor(hash, mask):
    result = ''
    for c in hash:
        result += chr(ord(c) ^ mask)
    for c in range(64-len(hash)):
        result += chr(mask)
    return result

def finalstep(input, magic_key_char, table):

    hash = md5.new(input).digest().encode('base64').translate(base64translate, '\r\n')

    sha1 = pysha.new(finalxor(hash, 0x36) + magic_key_char)
    if (table >= 3): sha1.count[1] = sha1.count[1] - 1
    digest1 = sha1.digest()

    digest2 = pysha.new(finalxor(hash, 0x5c) + digest1).digest()

    result = ''
    for i in range(10):
        # First two bytes of digest stuffed together.
        val = (ord(digest2[i * 2]) << 8) + ord(digest2[i*2+1])

        result += alphabet1[(val >> 0x0b) & 0x1f] + '='
        result += alphabet2[(val >> 0x06) & 0x1f]
        result += alphabet2[(val >> 0x01) & 0x1f]
        result += delimit_lookup[val & 0x01]

    return result

if __name__ == '__main__':

    def test(user, pwd, chal, str1true, str2true):
        print ''
        print "user: '%s'"% user
        print "pass: '%s'"% pwd
        print "chal: '%s'"% chal

        (str1,str2) = curphoo_process_auth(user, pwd, chal)

        status1 = 'FAILED'
        status2 = 'FAILED'
        if str1true == str1: status1 = 'PASSED'
        if str2true == str2: status2 = 'PASSED'

        print "str1: '%s' (%s)"%( str1, status1)
        print "str2: '%s' (%s)"%( str2, status2)

    test_cases = (
        ('username' , 'password', 'f%g|8%(p+4+f*l&h|d-h*(g^d*q^2&w+o+(x&i/o+4-3)/s^(d|j+j-a*3^u|(4&q%x))))', 'P=42,Q=1A;I=0B;Y=68,U=E9;L=2B;m=hf,K=34;m=id;J=5g,', 'w=8e;r=pl,H=bg;I=62,U=gA,A=36;O=F2,r=b0;P=ii,h=in;'),
        ('myuser'   , 'mypass'  , 'f%g|8%(p+4+f*l&h|d-h*(g^d*q^2&w+o+(x&i/o+4-3)/s^(d|j+j-a*3^u|(4&q%x))))', 'G=Ai,p=6B,W=f6,I=BB,I=CC;V=bp;P=17,p=ee;r=mj;p=eA;', 'k=8c,h=8h,Y=Eb;W=oo,h=jh,K=cd,J=6m,r=Fd;W=l2;Q=pi;'),
        ('username' , 'password', 'g*g/3&5-k-(4/i/c*d^v|r^m&s%2+(z*v%j%q|l-h+v|t^(b&4-q|2)|n)/8*l|z&x%v)'  , 'O=Cg,r=pb,N=bp,O=Fn;F=e8;F=33;p=l9;S=bj,m=A0;p=ci,', 'p=Bh,O=D1,T=f0;D=0B;G=ag;H=na,C=cB,E=4F;T=fg;A=2j;'),
        ('myuser'   , 'mypass'  , 'g*g/3&5-k-(4/i/c*d^v|r^m&s%2+(z*v%j%q|l-h+v|t^(b&4-q|2)|n)/8*l|z&x%v)'  , 'J=C9,w=1j,F=An,A=pg,D=AE;L=E7;P=lk;N=F0,Y=28,R=EC,', 'O=kf,r=4C;D=b9;J=nf,r=EC;E=2F;w=c4;k=em,G=8A,S=dE;'),
    )

    for user, pwd, chal, str1true, str2true in test_cases:
        test(user, pwd, chal, str1true, str2true)
