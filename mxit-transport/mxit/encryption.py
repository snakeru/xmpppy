import mxit.aes
from mxit.errors import *

def _text_array(text):
    """ Pad text to a multiple of 16 bytes.
    
    Similar to PKCS7 padding.
    """
    text = "<mxit/>" + text
        
    ar = map(ord, text)
    pads = 16 - (len(ar) % 16)
    ar += [0] * (pads-1)
    ar.append(pads)
    
    return ar
    
def _get_text(decoded):
    l = decoded[-1]
    text = ''.join(map(chr, decoded[:-l]))
    if text.startswith('<mxit/>'):
        return text[len('<mxit/>'):]
    else:
        raise MxitException('Invalid password')
    
    
def _key_array(key):
    """ Pad a key until it is exactly 16 bytes.
    
    Any characters after 16 are ignored.
    """
    key = map(ord, key)[:16]
    initial = map(ord, "6170383452343567")
    while len(key) < len(initial):
        key.append(initial[len(key)])
    return key
    
def client_id(jid):
    """ Calculate the portion of the client id that should be sent to the server. """
    n = int(jid[:2], 16)
    return jid[2:2+n]
    
def encode_password(jid, password):
    """ Encrypt the login password with the client id.
    
    A base64 representation of the encrypted password is returned, ready for transfer.
    """
    n = int(jid[:2], 16)
    key = jid[2+n:]
    encoded = encrypt(key, password)
    
    b64 = ''.join(map(chr, encoded)).encode('base64')
    return b64.strip()    # Remove /n

def _split(seq, size):
    for a in range(0, len(seq), size):
        yield seq[a:a+size]
    
def encrypt(key, text):
    """ Encrypt text with the given key.
    
    key -> any string with length smaller than or equal to 16
    text -> the data to encrypt, as a string
    
    Returns an array of bytes.
    """
    key = _key_array(key)
    text = _text_array(text)
    aes = mxit.aes.AES()
    parts = _split(text, 16)
    encoded = []
    for part in parts:
        encoded += aes.encrypt(part, key, aes.keySize["SIZE_128"])
    return encoded

def decrypt(key, encoded):
    """ Decrypt text that was encrypted with the given key.
    
    key -> any string with length smaller than or equal to 16
    encoded -> the encrypted data, either as an list of bytes, or a string, length must be a multiple of 16
    
    Returns the decrypted data as a string.
    """
    
    if isinstance(encoded, str):
        encoded = map(ord, encoded)
    key = _key_array(key)
    aes = mxit.aes.AES()
    
    parts = _split(encoded, 16)
    decoded = []
    for part in parts:
        decoded += aes.decrypt(part, key, aes.keySize["SIZE_128"]) 
    return _get_text(decoded)