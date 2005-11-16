# cpformat.py
# Copyright 2002 Alex Mercader <alex.mercader@iinet.net.au>
#
# This file is part of Curphoo.
#
# Curphoo is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Curphoo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Curphoo; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# $Id$
#
# $Log$
# Revision 1.1  2005-11-16 23:57:18  normanr
# Ported the curphoo code that was being used, to python.  This means no more need to recompile curphoo when you upgrade python.  Also yahoo transport now runs anywhere python does, and it's not limited to linux.
#
# Revision 1.1  2003/09/25 17:31:45  mkennedy
# intial import
#
# Revision 1.1  2002/05/01 08:39:22  hacker
# Initial revision
#
#
##

import re
import string
												# misc html tags
COLOR_TAG = re.compile('(</?black>|</?red>|</?blue>|</?orange>|</?purple>|</?magenta>|</?cyan>|</?green>|</?yellow>|</?white>|</?gray>|</?b>|</?u>|</?i>)', re.I)

FONT_TAG = re.compile('</?font.*?>', re.I)

FADE_TAG = re.compile('</?fade.*?>', re.I)

ALT_TAG = re.compile('</?alt.*?>', re.I)

												# cheetachat crap control
SND_TAG = re.compile('</?snd.*?>', re.I)
												# ECMA-48 SGR sequence
ESC_SEQ = re.compile(r'\033\[.*?m')

MULTI_NL = re.compile('\n+', re.M)

def no_nonprint(text):
	result = ''
	for ch in text:
		if ch in string.printable:
			result = "%s%s" % (result, ch)
	return result

def no_all_caps(s):
	lw = s.split()
	nupper = 0; nlower = 0			# count words in all caps
	for w in lw:
		if w.isupper(): nupper += 1
		else: nlower += 1
	if nupper > nlower:
		if nupper == 1:
			if len(w) > 9:			# allowing single WORD with
				s = s.lower()		# less than 9 characters
		else:
			s = s.lower()			# user had caps lock on, modify
	return s

def squeeze_lines(s):
	a = s.split('\n')
	a = [l for l in a if l.strip()]
	a.reverse()
	b = ['']
	for e in a:
		if e != b[0]:
			b.insert(0, e)
	b.pop()
	return '\n'.join(b)

def do(text, sess = None):
	text = ESC_SEQ.sub('', text)
	text = text.replace('\x0d\x0a', ' ')
	text = text.replace('\x0d', '')
	text = COLOR_TAG.sub('', text)
	text = FONT_TAG.sub('', text)
	text = FADE_TAG.sub('', text)
	text = ALT_TAG.sub('', text)
	text = SND_TAG.sub('', text)
	text = squeeze_lines(text)
	text = MULTI_NL.sub('\n', text)
	if (sess != None and sess.rc['auto-lowercase'].upper() == 'Y'):
		text = no_all_caps(text)
	text = no_nonprint(text)
	text = text.strip()
	return text

