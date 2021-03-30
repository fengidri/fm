import os
import time
import logging

from . import db
from . import send
from . import syncmail
from . import conf
from . import mail
from . import topic

Mail = mail.Mail

conf = conf.conf

sendmail = send.sendmail

class Mbox(object):
    def __init__(self, mbox, thread = True, preload = 0, archived = 0):
        self.top = []
        self.isbuiltin = False
        self.thread_show = thread
        self.topics = []

        if mbox == 'Sent':
            self.isbuiltin = True
            self.thread_show = False

        self.mbox = mbox

        if self.thread_show:
            self.topics = topic.db_load_topic(mbox, archived)
            self.topics.sort(key = lambda x: x.timestamp(), reverse = True)
            if preload:
                topic.batch_load_mails(self.topics[0:preload])
        else:
            self.top = db.index.filter(mbox = mbox).select()
            self.top.sort(key = lambda x: x.Date_ts())

    def get_topics(self):
        return self.topics

    def output(self, reverse = False):
        top = self.top
        if reverse:
            top = top[::-1]

        o = []
        for m in top:
            m.output(o)
        return o

    def mark_readed(self):
        db.index.filter(mbox = self.mbox).update(status = 1)
        db.class_names.dec_unread(self.mbox, 0)


