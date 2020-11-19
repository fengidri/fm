# -*- coding:utf-8 -*-


import os
import time
from . import db
from . import send
from . import syncmail
from . import conf

conf = conf.conf

sendmail = send.sendmail

class g:
    db = None
    msgid = 0

def gen_msgid():
    g.msgid += 1
    return "<%s-%s-%s>" % (time.time(), g.msgid, conf.me)

class Mbox(object):
    def __init__(self, dirname):
        self.top = []
        self.mail_map = {}
        self.mail_list = []
        self.isbuiltin = False

        if os.path.basename(dirname) == 'Sent':
            self.isbuiltin = True

        self.mbox = os.path.basename(dirname)

        s = time.time()
        self.load_db()
        #print("load mbox index list from db: %s" % (time.time() -s))

        s = time.time()
        if self.isbuiltin:
            self.top = self.mail_list
        else:
            self.thread()

        g.db.commit()
        print("load thread: %s" % (time.time() -s))


    def load_db(self):
        for m in mail.mail_db_mbox(self.mbox):
            self.mail_list.append(m)
            self.mail_map[m.Message_id()] = m

    def thread(self):
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

if __name__ == '__main__':
    import sys
    sendmail(sys.argv[1])



