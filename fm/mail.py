# -*- coding:utf-8 -*-

import base64
import quopri
import os
import datetime
import time
import json
import logging
import functools

import email
import email.utils
from email.header import decode_header
from email.mime.text import MIMEText
from email.header import Header

from . import conf

conf = conf.conf


def decode(h):
    h = decode_header(h)[0]

    if h[1]:
        h = h[0].decode(h[1])
    else:
        h = h[0]
        if isinstance(h, bytes):
            h = h.decode("utf-8")
    return h

def header_parse_msgid(h):
    if not h:
        return ''

    h = h.replace('\n', ' ')
    h = h.strip()

    if h[0] == '<':
        p = h.find('>')
        if p == -1:
            return ''

        return h[0:p + 1]



class EmailAddr(object):
    def __init__(self, addr):
        self.name   = ''
        self.server = ''
        self.alias  = ''
        self.short  = ''
        self.addr   = ''
        self.isme   = False

        addr = addr.strip()

        i = addr.find('<')
        if i > 0:
            name = addr[0:i].strip()
            if name[0] == '"':
                name = name[1:-1]

            self.alias = decode(name)
            self.addr = addr[i + 1:-1]
        else:
            self.alias = None
            self.addr = addr

        if '@' in self.addr:
            self.name, self.server = self.addr.split('@')
        else:
            self.name = self.addr
            self.server = ''

        if self.addr == conf.me:
            self.short = 'Me'
            self.isme = True
        else:
            if self.alias:
                self.short = self.alias
            else:
                self.short = self.name

    def format(self): #
        if not self.alias:
            return self.addr
        return '%s <%s>' % (self.alias, self.addr)

    def to_str(self): # return ascii string. =?UTF-8?xxxxxxx==?= <xxxx@xxxx.com>
        if self.alias:
            alias = self.alias
            if not alias.isascii():
                alias = Header(alias, 'utf-8').encode()
            return "%s <%s>" % (alias, self.addr)

        return '%s@%s' % (self.name, self.server)

    def simple(self): # name@server.com
        return '%s@%s' % (self.name, self.server)



class EmailAddrLine(list):
    def __init__(self, line):
        list.__init__(self)

        line = line.strip().replace('\n', '').replace('\r', '')

        s = 0
        skip = False
        for i, c in enumerate(line):
            if skip:
                if c == '"':
                    skip = False
                continue

            if c == '"':
                skip = True
                continue

            if c == ',':
                addr = line[s: i].strip()
                self.append(EmailAddr(addr))
                s = i + 1

        addr = line[s:].strip()
        if addr:
            self.append(EmailAddr(addr))

    def format(self):
        return ', '.join([x.format() for x in self])

    def simple(self):
        return ', '.join([x.simple() for x in self])

    def simple_list(self):
        return [x.simple() for x in self]

    def to_str(self):
        return ', '.join([x.to_str() for x in self])

    def to_str_list(self):
        return [x.to_str() for x in self]

class M(object):
    def __init__(self):
        self.topic = None

        self.sub_n = 0
        self.parent = None
        self.sub_thread = []
        self.mail = None
        self.isnew = False
        self.path = None
        self.isfirst = False
        self.islast = False
        self.thread_head = None

        self.header_in_reply_to = None
        self.header_message_id = None

        self.fold = None # for vim plugin
        self.topic_id = None

    def get_mail(self):
        if self.mail:
            return self.mail

        for e in ['UTF-8', 'Latin-1']:
            try:
                c = open(self.path, encoding = e).read()
                break
            except UnicodeDecodeError:
                pass
        else:
            raise 'UnicodeDecodeError: %s' % self.path

        self.size = len(c)

        self.mail = email.message_from_string(c)
        return self.mail

    def __body(self, part):
        m = part.get_payload(None, False)
        charset = part.get_charset()
        if not charset:
            charset = 'UTF-8'

        cte = part.get('Content-Transfer-Encoding')

        if isinstance(m, bytes):
            m = m.decode(charset)

        if cte == 'quoted-printable':
            m = quopri.decodestring(m)
            m = m.decode('UTF-8')

        if cte == 'base64':
            m = base64.b64decode(m)
            m = m.decode('UTF-8')

        return m


    def Body(self):
        b = self.get_mail()

        tp = ['text/plain', 'text/html']

        for t in tp:
            for part in b.walk():
                if part.get_content_type() == t:
                    return self.__body(part)
        return ''

    def header(self, header):
        h = self.get_mail().get(header, '')
        return decode(h)

    def real_header(self, h):
        s = self.get_mail().get(h, '')
        return EmailAddrLine(s)

    def Attachs(self):
        b = self.get_mail()

        tp = ['text/plain', 'text/html']
        att = []

        for part in b.walk():
            t = part.get_content_type()
            if t in tp:
                continue
            att.append((t, len(part.get_payload())))
        return att

    def append(self, m):
        self.sub_thread.append(m)
        m.parent = self

        return True

    def mark_readed(self, thread = False, unread = False):
        if self.isnew:
            self.isnew = False
            db.index.filter(rowid = self.rowid).update(status = 1)
        elif unread:
            self.isnew = True
            db.index.filter(rowid = self.rowid).update(status = 0)

        if thread:
            for sub in self.sub_thread:
                sub.mark_readed(True, unread)

    def last_recv_ts(self):
        ts = self.Date_ts()

        for m in self.sub_thread:
            t = m.last_recv_ts()
            if t > ts:
                ts = t
        return ts

    def num(self):
        s = 1
        for m in self.sub_thread:
            s += m.num()

        return s

    def thread(self, index, head):
        self.index = index
        self.thread_head = head

        if not self.sub_thread:
            return

        def cmpfun(a, b):
            a_ts = a.Date_ts()
            b_ts = b.Date_ts()

            d = a_ts - b_ts
            if d > -2 and d < 2:
                if a.Subject() > b.Subject():
                    return 1
                else:
                    return -1
            return d


        self.sub_thread.sort(key = functools.cmp_to_key(cmpfun))
        self.sub_thread[0].isfirst = True
        self.sub_thread[-1].islast = True

        for m in self.sub_thread:
            m.thread(index + 1, head)

    def news(self):
        n = 0
        for m in self.sub_thread:
            n += m.news()

        if self.isnew:
            n += 1

        return n


    def str(self):
        subject = self.Subject()

        return '%s%s' % (self.thread_prefix(), subject)

    def is_reply(self):
        subject = self.Subject()
        if subject[0:3].lower() == 're:':
            if self.parent:
                return True
        return False


    def thread_prefix(self, user = None):
        if self.index == 0:
            return ''

        prefix = '->'

        #if self.index > 0:
        #    if self.isfirst:
        #    else:
        #        prefix = '|->'
        #else:
        #    prefix = ''
        p = self
        while p.parent.parent:
            p = p.parent

        if p.islast:
            return ' %s|%s' % ('  ' * (self.index - 1),  prefix)
        else:
            return ' |%s%s' % ('  ' * (self.index - 1),  prefix)


    def output(self, o):
        o.append(self)

        for i, m in enumerate(self.sub_thread):
            m.output(o)


# this init from file path
class Mail(M):
    def __init__(self, path):
        M.__init__(self)
        self.path = path
        self.flag = 0

    def Subject(self):
        s = self.header('Subject')

        return s.replace('\n', '').replace('\r', '')

    def In_reply_to(self):
        if not self.header_in_reply_to:
            r = self.get_mail().get("In-Reply-To", '')
            r = r.split('\n')[0].strip()
            r = header_parse_msgid(r)
            self.header_in_reply_to = r
        else:
            r = self.header_in_reply_to

        if r == self.Message_id:
            r = ''

        return r

    def Message_id(self):
        if not self.header_message_id:
            msgid = self.get_mail().get("Message-Id")
            msgid = header_parse_msgid(msgid)
            if msgid == None:
                f = self.From()
                filename = os.path.basename(self.path)
                msgid = "<%s-%s-%s@%s>" % (time.time(), filename, f.name, f.server)
            else:
                msgid = msgid.strip()

            self.header_message_id = msgid

        return self.header_message_id

    def Date(self):
        d= self.get_mail().get("Date")
        if not d:
            d = 'Mon, 01 Jul 1979 00:00:00 +0800'
        return d

    def From(self):
        s = self.get_mail().get('From', '')
        l = EmailAddrLine(s)
        if l:
            return l[0]
        return EmailAddr('')

    def To(self):
        s = self.get_mail().get("TO", '')
        return EmailAddrLine(s)

    def Cc(self):
        s = self.get_mail().get("Cc", '')
        return EmailAddrLine(s)

    def Date_ts(self):
        d = email.utils.parsedate_tz(self.Date())
        if not d:
            return 0
        return email.utils.mktime_tz(d)


from . import db
