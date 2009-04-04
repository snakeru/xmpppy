#!/usr/bin/python
# -*- coding: UTF-8 -*- 

"Localized strings from xmppd.py"

# English XMPPD Strings
# Copyright (c) 2005 Kristopher Tate
en_server_localized_strings="""
session-receive-error -- en -- Socket error while receiving data!
session-send-error -- en -- Socket error while sending data!
session-admin-set -- en -- Setting local user <%s> as administrator.
server-node-registered -- en -- Registered %(fileno)s using %(method)s (%(raw)s) %(socker_notice)s
server-node-unregistered -- en -- UNregistered %(fileno)s (%(raw)s)
server-s2s-attempt-connection -- en -- 'Attempting connection with server %(server)s...
server-shutdown-msg -- en -- Due to a console request, the server is now preparing to shutdown...
server-s2s-thread-error -- en -- There was an error with this thread: %s
server-pvcy-activated -- en -- ###PRIVACY SUBSYSTEM :: MODE ACTIVATED
server-pvcy-access-check -- en -- ###PRIVACY SUBSYSTEM :: Checking JID <%(jid_from)s> for access on <%(jid_to)s> ###
server-pvcy-access-clear-oneway -- en -- ###PRIVACY SUBSYSTEM :: JID <%(jid_from)s> IS CLEARED FOR ONEWAY[->] ACCESS WITH <%(jid_to)s>###
server-pvcy-access-clear-oneway-presence -- en -- ###PRIVACY SUBSYSTEM :: JID <%(jid_from)s> IS CLEARED FOR ONEWAY[->] ACCESS WITH <%(jid_to)s> for presence::xSubscript ONLY###
server-pvcy-access-clear-unlimited -- en -- ###PRIVACY SUBSYSTEM :: JID <%(jid_from)s> IS CLEARED FOR UNLIMITED ACCESS TO <%(jid_to)s> ###
server-pvcy-access-clear-bidirectional -- en -- ###PRIVACY SUBSYSTEM :: JID <%(jid_from)s> IS CLEARED FOR BIDIRECTIONAL[<-->] ACCESS WITH <%(jid_to)s> ###
server-pvcy-access-notclear-doublefalse -- en -- ###PRIVACY SUBSYSTEM :: JID <%(jid_from)s> IS NOT ALLOWED ACCESS TO <%(jid_to)s> [ANON_ALLOW=FALSE::TO_RS_ITEM=FALSE]###
server-pvcy-access-notclear-modeto -- en -- ###PRIVACY SUBSYSTEM :: JID <%(jid_from)s> IS NOT ALLOWED ACCESS TO <%(jid_to)s> [MODE=TO]###
server-pvcy-access-notclear-falseanon -- en -- ###PRIVACY SUBSYSTEM :: JID <%(jid_from)s> IS NOT ALLOWED ACCESS TO <%(jid_to)s> [ANON_ALLOW=FALSE]###"""

# French XMPPD Strings
# Copyright (c) 2005 Eoban Binder
fr_server_localized_strings="""
session-receive-error -- fr -- Erreur de réseau tout en recevant des données
session-send-error -- fr -- Erreur de réseau tout en envoyant des données
session-admin-set -- fr -- Nous plaçons l'utilisateur appelé <%s> en tant qu'administrateur.
server-node-registered -- fr -- Enregistré %(fileno)s en utilisant %(method)s (%(raw)s %(socker_notice)s
server-node-unregistered -- fr -- Enlevé %(fileno)s (%(raw)s)
server-s2s-attempt-connection -- fr -- Nous essayons de nous relier au serveur appelé %(server)s...
server-shutdown-msg -- fr -- En raison d'une demande de la console de commande, le serveur prépare pour s'arrêter...
server-s2s-thread-error -- fr -- Il y avait une erreur avec ce fil: %s
server-pvcy-activated -- fr -- ###SYSTÈME D'INTIMITÉ :: LE MODE A ÉTÉ ACTIVÉ
server-pvcy-access-check -- fr -- ###SYSTÈME D'INTIMITÉ :: Nous examinons JID <%(jid_from)s> pour assurer l'accès à <%(jid_to)s> ###
server-pvcy-access-clear-oneway -- fr -- ###SYSTÈME D'INTIMITÉ :: JID <%(jid_from)s> EST APPROUVÉ POUR L'ACCÈS EN SENS UNIQUE[->] À <%(jid_to)s>###
server-pvcy-access-clear-oneway-presence -- fr -- ###SYSTÈME D'INTIMITÉ :: JID <%(jid_from)s> EST APPROUVÉ POUR L'ACCÈS EN SENS UNIQUE[->] À <%(jid_to)s> pour presence::xSubscript SEULEMENT###
server-pvcy-access-clear-unlimited -- fr -- ###SYSTÈME D'INTIMITÉ :: JID <%(jid_from)s> EST APPROUVÉ POUR L'ACCÈS TOTAL <%(jid_to)s> ###
server-pvcy-access-clear-bidirectional -- fr -- ###SYSTÈME D'INTIMITÉ :: JID <%(jid_from)s> EST APPROUVÉ POUR L'ACCÈS BIDIRECTIONNEL[<-->] À <%(jid_to)s> ###
server-pvcy-access-notclear-doublefalse -- fr -- ###SYSTÈME D'INTIMITÉ :: JID <%(jid_from)s> N'EST PAS APPROUVÉ POUR L'ACCÈS À <%(jid_to)s> [ANON_ALLOW=FALSE::TO_RS_ITEM=FALSE]###
server-pvcy-access-notclear-modeto -- fr -- ###SYSTÈME D'INTIMITÉ :: JID <%(jid_from)s> N'EST PAS APPROUVÉ POUR L'ACCÈS À <%(jid_to)s> [MODE=TO]###
server-pvcy-access-notclear-falseanon -- fr -- ###SYSTÈME D'INTIMITÉ :: JID <%(jid_from)s> N'EST PAS APPROUVÉ POUR L'ACCÈS À <%(jid_to)s> [ANON_ALLOW=FALSE]###"""

# Japanese XMPPD Strings
# Copyright (c) 2005 Kristopher Tate
# Special thanks to 大下 拓也 (Takuya Ohshita) for some technical clarification!
ja_server_localized_strings="""
session-receive-error -- ja -- データを受け取っている間、ソケット・エラーが起きました。
session-send-error -- ja -- データを送っている間、ソケット・エラーが起きました。
session-admin-set -- ja -- Adminとしてユーザ<%s>を設定中・・・
server-node-registered -- ja -- %(method)sで%(fileno)sを登録しました (%(raw)s) %(socker_notice)s
server-node-unregistered -- ja -- %(fileno)sの登録を削除しました。 (%(raw)s)
server-s2s-attempt-connection -- ja -- S2Sでサーバー%(server)sに接続中・・・
server-shutdown-msg -- ja -- コンソールからのリクエストでサーバーをシャットダウンしています
server-s2s-thread-error -- ja -- エラーが以下のスレッドで発生しました: %s
server-pvcy-activated -- ja -- ###プライバシー・サブシステム :: モードが活性化されました"""

globals()['LANG_LIST'] += [en_server_localized_strings,fr_server_localized_strings,ja_server_localized_strings]