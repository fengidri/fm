# -*- coding:utf-8 -*-


import os
import time
import logging
from . import db
from . import send
from . import syncmail
from . import conf
from . import mail

Mail = mail.Mail

conf = conf.conf

sendmail = send.sendmail

class g:
    db = None
    msgid = 0

def gen_msgid():
    g.msgid += 1
    return "<%s-%s-%s>" % (time.time(), g.msgid, conf.me)

class Mbox(object):
    def __init__(self, dirname, thread = True):
        self.top = []
        self.mail_map = {}
        self.mail_list = []
        self.isbuiltin = False
        self.thread_show = thread

        if os.path.basename(dirname) == 'Sent':
            self.isbuiltin = True
            self.thread_show = False

        self.mbox = os.path.basename(dirname)

        s = time.time()
        self.load_db()

        s = time.time()
        if self.thread_show:
            self.thread()
        else:
            self.top = self.mail_list

        g.db.commit()

        print("load thread: %s" % (time.time() -s))


    def load_db(self):
        for m in mail.mail_db_mbox(self.mbox):
            self.mail_list.append(m)
            self.mail_map[m.Message_id()] = m

    def _move(self, target, m):
        target.append(m)
        self.tmap[m.Message_id()] = m

    def find_upper(self, m):
        if m in self.mail_list:
            self.mail_list.remove(m)

        msgid = m.Message_id()
        if msgid in self.mail_map:
            del self.mail_map[msgid]

        r = m.In_reply_to()
        if not r:
            self._move(self.top, m)
            return

        p = self.tmap.get(r)
        if p:
            self._move(p, m)
            return

        p = self.mail_map.get(r)
        if p:
            self.find_upper(p)
            self._move(p, m)
            return

        p = mail.mail_db_msgid(r)
        if p:
            self.find_upper(p)
            self._move(p, m)
            return

        self._move(self.top, m)

    def thread(self):
        self.tmap = {}
        self.top = []
        for m in self.mail_list:
            self.find_upper(m)

        self.top.sort(key = lambda x: x.last_recv_ts())

        for m in self.top:
            m.thread(0, m)


    def _thread(self):
        for m in self.mail_list:
            r = m.In_reply_to()
            if not r:
                self.top.append(m)
                continue

            while r:
                p = self.mail_map.get(r)
                if p:
                    p.append(m)
                    break

                t = mail.mail_db_msgid(r)
                if t:
                    self.mail_map[t.Message_id()] = t
                    t.append(m)
                    m = t
                    r = m.In_reply_to()
                    if r:
                        continue

                self.top.append(m)
                break

        self.top.sort(key = lambda x: x.last_recv_ts())

        for m in self.top:
            m.thread(0, m)

    def output(self, reverse = False):
        top = self.top
        if reverse:
            top = top[::-1]

        o = []
        for m in top:
            m.output(o)
        return o


g.db = db.db

