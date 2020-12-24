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

class Mbox(object):
    def __init__(self, dirname, thread = True):
        self.top = []
        self.mail_map = {}
        self.mail_list = []
        self.isbuiltin = False
        self.thread_show = thread
        self.topics = []

        if os.path.basename(dirname) == 'Sent':
            self.isbuiltin = True
            self.thread_show = False

        self.mbox = os.path.basename(dirname)

        s = time.time()
        if self.thread_show:
            self.load_db()
            self.thread()
        else:
            self.top = mail.mail_db_mbox(self.mbox)
            self.top.sort(key = lambda x: x.last_recv_ts())

        db.db.commit()

        print("load thread: %s" % (time.time() -s))

    def load_db(self):
        mails = mail.mail_db_mbox(self.mbox)
        for m in mails:
            msgid = m.Message_id()
            l = self.mail_map.get(msgid)
            if l:
                l.append(m)
            else:
                self.mail_map[msgid] = m
                self.mail_list.append(m)

    def top_mail(self, m):
        self.top.append(m)
        if not m.topic:
            m.topic = mail.Topic()
            m.topic.mails.append(m)
            m.topic.default_top = m

        m.topic.mbox = self.mbox

        self.topics.append(m.topic)

    def find_upper(self, m):
        if m.parent or m in self.top:
            return

        r = m.In_reply_to()
        msgid = m.Message_id()
        if not r or r == msgid:
            self.top_mail(m)
            return

        p = self.mail_map.get(r)
        if p:
            p.append(m)
            self.find_upper(p)
            return

        t = mail.mail_db_msgid(r)
        if not t:
            self.top_mail(m)
            return

        t.copy(self.mbox)

        self.mail_map[t.Message_id()] = t
        t.append(m)
        self.find_upper(t)


    def thread(self):
        for m in self.mail_list:
            self.find_upper(m)

        topic_map = {}
        topic_list = []

        for topic in self.topics:
            topic.done()
            tp = topic.topic()
            one = topic_map.get(tp)
            if one:
                one.marge(topic)
            else:
                topic_map[tp] = topic
                topic_list.append(topic)

        self.topics = topic_list
        self.topics.sort(key = lambda x: x.timestamp(), reverse=True)

        for tp in self.topics:
            tp.thread()

    def output(self, reverse = False):
        top = self.top
        if reverse:
            top = top[::-1]

        o = []
        for m in top:
            m.output(o)
        return o



