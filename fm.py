# -*- coding:utf-8 -*-


import os
import email
import datetime
import time
import json
from email.header import decode_header
import subprocess


def decode(h):
    h = decode_header(h)[0]

    if h[1]:
        h = h[0].decode(h[1])
    else:
        h = h[0]
        if isinstance(h, bytes):
            h = h.decode("utf-8")
    return h

class EmailAddr(object):
    def __init__(self, addr):
        addr = addr.strip()

        i = addr.find('<')
        if i > 0:
            name = addr[0:i].strip()
            if name[0] == '"':
                name = name[1:-1]

            self.alias = decode(name)
            self.addr = addr[i + 1:-1]
            self.name, self.server = self.addr.split('@')
        else:
            self.alias = None
            self.addr = addr
            self.name, self.server = self.addr.split('@')

        if self.addr == conf.me:
            self.short = ''
        else:
            if self.alias:
                self.short = self.alias
            else:
                self.short = self.name





class Mail(object):
    def __init__(self, path):
        self.parent = None
        self.sub_thread = []

        for e in ['UTF-8', 'Latin-1']:
            try:
                c = open(path, encoding = e).read()
                break
            except UnicodeDecodeError:
                pass
        else:
            raise 'UnicodeDecodeError: %s' % path



        self.mail = email.message_from_string(c)
        self.isnew = False
        self.path = path
        self.isfirst = False
        self.islast = False
        self.thread_head = None

        self.header_in_reply_to = None
        self.header_message_id = None


    def mark_readed(self):
        name = os.path.basename(self.path)

        cur = os.path.dirname(self.path)
        cur = os.path.dirname(cur)
        cur = os.path.join(cur, 'cur')
        cur = os.path.join(cur, name)

        os.rename(self.path, cur)
        self.path = cur

    def header(self, header):
        h = self.mail.get(header)
        return decode(h)


    def In_reply_to(self):
        if not self.header_in_reply_to:
            self.header_in_reply_to = self.mail.get("In-Reply-To", '').strip()

        return self.header_in_reply_to

    def Message_id(self):
        if not self.header_message_id:
            self.header_message_id = self.mail.get("Message-Id", '').strip()

        return self.header_message_id

    def Date(self):
        d= self.mail.get("Date")
        if not d:
            d = 'Mon, 01 Jul 1979 00:00:00 +0800'
        return d

    def From(self):
        return self.mail.get('From')

    def To(self):
        return self.mail.get("TO")

    def Cc(self):
        return self.mail.get("Cc")

    def Date_ts(self):
        d = self.mail.get("Date")
        if not d:
            d = 'Mon, 27 Jul 2020 10:32:31 +0800'
        d = email.utils.parsedate_tz(d)
        return email.utils.mktime_tz(d)

    def Subject(self):
        s = self.header('Subject')

        return s.replace('\n', '').replace('\r', '')


    def Body(self):
        b = self.mail

        tp = ['text/plain', 'text/html']

        for t in tp:
            for part in b.walk():
                if part.get_content_type() == t:
                    m = part.get_payload(None, False)
                    if isinstance(m, bytes):
                        return m.decode('UTF-8')
                    else:
                        return m
        return ''

    def Attachs(self):
        b = self.mail

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

    def last_recv_ts(self):

        ts = self.Date_ts()

        for m in self.sub_thread:
            t = m.Date_ts()
            if t > ts:
                ts = t
        return ts

    def num(self):
        s = 1
        for m in self.sub_thread:
            s += m.num()

        return s

    def sort(self, index, head):
        self.index = index

        self.thread_head = head

        if not self.sub_thread:
            return

        self.sub_thread.sort(key = lambda x: x.Date_ts())
        self.sub_thread[0].isfirst = True
        self.sub_thread[-1].islast = True

        for m in self.sub_thread:
            m.sort(index + 1, head)


    def str(self):
        subject = self.Subject()

        return '%s%s' % (self.thread_prefix(), subject)

    def thread_prefix(self):
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




class Mbox(object):
    def __init__(self, dirname):
        self.top = []
        self.mail_list = []
        self.mail_map = {}

        new = os.path.join(dirname, 'new')
        cur = os.path.join(dirname, 'cur')

        self.load(new, True)
        self.load(cur, False)

        for m in self.mail_list:
            r = m.In_reply_to()
            if not r:
                self.top.append(m)
                continue

            p = self.mail_map.get(r)
            if p:
                p.append(m)
            else:
                self.top.append(m)

        self.sort()


    def load(self, dirname, isnew):
        for path in os.listdir(dirname):
            path = os.path.join(dirname, path)

            m = Mail(path)
            m.isnew = isnew

            self.mail_list.append(m)
            self.mail_map[m.Message_id()] = m


    def sort(self):
        self.top.sort(key = lambda x: x.last_recv_ts())

        for m in self.top:
            m.sort(0, m)

    def output(self, reverse = False):
        top = self.top
        if reverse:
            top = top[::-1]

        o = []
        for m in top:
            m.output(o)
        return o

def sendmail(path):
    c = open(path).read()
    p = subprocess.Popen(['msmtp', '-t'],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)

    stdout, stderr = p.communicate(c)

    code = p.returncode

    if 0 == code:
        name = os.path.basename(name)
        sent = os.path.join('~/.fm.d/sent', name)
        open(sent, 'w').write(c)

        os.remove(path)

    return code, stdout, stderr


class Conf:
    def __init__(self):
        path = '~/.fm.json'
        path = os.path.expanduser(path)
        j = open(path).read()
        c = json.loads(j)

        default = c.get('default')

        self.mbox = []

        p = os.path.expanduser(c['deliver'])

        for d in os.listdir(p):
            dd = os.path.join(p, d)
            if os.path.isdir(dd):
                box = {'path':dd}
                box['name'] = d

                if d == default:
                    box['default_mbox'] = True

                self.mbox.append(box)

        self.me = c.get('user')
        self.name = c.get('name', self.me.split('@')[0])

conf = Conf()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        m = Mail(path)
        print(m.Body())

    else:
        mbox = Mbox(conf.mbox[1]['path'])
        head = None
        for m in mbox.output():
            if m.thread_head != head:
                print('')
                head = m.thread_head

            print(m.str())



