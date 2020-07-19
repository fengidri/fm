# -*- coding:utf-8 -*-


import os
import email
import datetime
import time
import json
from email.header import decode_header

class EmailAddr(object):
    def __init__(self, addr):
        addr = addr.strip()

        i = addr.find('<')
        if i > 0:
            name = addr[0:i].strip()
            if name[0] == '"':
                name = name[1:-1]

            self.name = name
            self.addr = addr[i + 1:-1]
            self.server = self.addr.split('@')[1]
        else:
            self.addr = addr
            self.name, self.server = self.addr.split('@')

        if self.addr == conf.me:
            self.short = ''
        else:
            self.short = self.name





class Mail(object):
    def __init__(self, path):
        self.parent = None
        self.sub_thread = []

        c = open(path).read()

        self.mail = email.message_from_string(c)
        self.isnew = False
        self.path = path
        self.isfirst = False
        self.islast = False
        self.thread_head = None

    def mark_readed(self):
        name = os.path.basename(self.path)

        cur = os.path.dirname(self.path)
        cur = os.path.dirname(cur)
        cur = os.path.join(cur, 'cur')
        cur = os.path.join(cur, name)

        os.rename(self.path, cur)


    def In_reply_to(self):
        return self.mail.get("In-Reply-To", '').strip()

    def Message_id(self):
        return self.mail.get("Message-Id", '').strip()

    def Date(self):
        return self.mail.get("Date")

    def From(self):
        return self.mail.get("From")

    def To(self):
        return self.mail.get("TO")

    def Cc(self):
        return self.mail.get("Cc")

    def Date_ts(self):
        d = self.mail.get("Date")
        d = email.utils.parsedate(d)
        return time.mktime(d)

    def Subject(self):
        subject = self.mail.get('Subject').replace('\n', '').replace('\r', '')
        subject = decode_header(subject)[0]

        if subject[1]:
            subject = subject[0].decode(subject[1])
        else:
            subject = subject[0]
        return subject

    def Body(self):
        b = self.mail

        if b.is_multipart():
            for payload in b.get_payload():
                return payload.get_payload()
        else:
            return b.get_payload()

        #body = self.mail.get_body(('plain',))
        #if body:
        #    return body.get_content()
        #return ''

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

        new = os.path.join(dirname, 'new')
        cur = os.path.join(dirname, 'cur')

        self.load(new, True)
        self.load(cur, False)

        for m in self.mail_list:
            if not m.In_reply_to():
                self.top.append(m)
                continue

            for mm in self.mail_list:
                if mm.Message_id() == m.In_reply_to():
                    mm.sub_thread.append(m)
                    m.parent = mm
                    break
            else:
                self.top.append(m)

        self.sort()


    def load(self, dirname, isnew):
        for path in os.listdir(dirname):
            path = os.path.join(dirname, path)

            m = Mail(path)
            m.isnew = isnew

            self.mail_list.append(m)


    def sort(self):
        self.top.sort(key = lambda x: x.Date_ts())

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

class Conf:
    def __init__(self):
        path = '~/.fm.json'
        path = os.path.expanduser(path)
        j = open(path).read()
        c = json.loads(j)

        self.mbox = []
        for p in c['mbox']:
            self.mbox.append(os.path.expanduser(p))

        self.me = c.get('me')

conf = Conf()

if __name__ == '__main__':

    mbox = Mbox(conf.mbox[0])
    head = None
    for m in mbox.output():
        if m.thread_head != head:
            print('')
            head = m.thread_head

        print(m.str())



