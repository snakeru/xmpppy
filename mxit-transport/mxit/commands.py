from mxit.enum import Enumeration

Client = Enumeration('Client', [
    ('LOGIN', 1),
    ('LOGOUT', 2 ),
    ('EDIT_BUDDY', 5),
    ('INVITE', 6),
    ('REMOVE_BUDDY', 8),
    ('PING', 9),
    ('MESSAGE', 10),
    ('PROFILE', 12),
    ('PROFILE_REQUEST', 26),
    ('BINARY', 27),
    ('RENAME_GROUP', 29),
    ('PRESENCE', 32),
    ('MOOD', 41),
    ('CREATE_ROOM', 44),
    ('ROOM_INVITE', 45),
    ('ACCEPT_INVITE', 52),
])

Binary = Enumeration('Binary', [
    ('SPLASH', 1),
    ('FILEDESC', 6),
    ('REQUEST_FILE', 8),
    ('ACK_FILE', 9),
    ('SEND_FILE', 10),
    ('FORWARD_FILE', 11),
])

Server = Enumeration('Server', [
    ('LOGOUT', 2),
    ('PRESENCE', 3),
    ('MESSAGE', 9),
    ('INVITE_RECEIVED', 51),
    ('BINARY', 27),
])