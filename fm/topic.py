# -*- coding:utf-8 -*-

from . import db
from . import mail
from collections import defaultdict

def batch_load_mails(topics):
    mails = db.index.batch_load_topics(topics)

    ms = defaultdict(list)
    for m in mails:
        ms[m.topic_id].append(m)

    for topic in topics:
        topic.load(mails = ms.get(topic.db.id, []))

"""
    创建一个新的 topic 纪录, 但是 mbox 不同
"""
def topic_dup(topic, mbox):
    db.topic.insert(topic, id = topic.get_id(), mbox = mbox)

# 合并多个 mail 到同一个 topic, 如果有多个 mbox
# 存在, 就为对应的 mbox 创建一条相同 topic_id 的 topic 纪录
def topic_merge(dst, src):
    db.set_delay()

    # 获取 dst (topic id) 所有的 mbox
    mboxs = ['Sent']
    for t in db.topic.filter(id = dst).select():
        if t.db.mbox not in mboxs:
            mboxs.append(t.db.mbox)

    for i in src:
        mails = db.index.filter(topic_id = i).select()
        for m in mails:
            if m.mbox not in mboxs:
                mboxs.append(m.mbox)
                tp = Topic(m)
                db.topic.insert(tp, id = dst)

            db.index.filter(rowid = m.rowid).update(topic_id = dst)

        db.topic.filter(id = i).delete()

    db.commit()

def db_load_topic(mbox, archived):
    if archived:
        archived = 1
    else:
        archived = 0

    o = []
    topic = {}
    for t in db.topic.filter(mbox = mbox, archived = archived).select():
        last = topic.get(t.topic())
        if last:
            topic_merge(last.db.id, [t.db.id])
            continue

        topic[t.topic()] = t

        o.append(t)

    return o

class TopicDb(object):
    def __init__(self, record, obj):
        record = list(record)
        self.rowid       = record.pop(0)
        self.id          = record.pop(0)
        self.topic       = record.pop(0)
        self.mbox        = db.class_names.getname(record.pop(0))
        self.first_ts    = record.pop(0)
        self.last_ts     = record.pop(0)
        self.sponsor     = record.pop(0)
        self.participant = record.pop(0)
        self.mail_n      = record.pop(0)
        self.thread_n    = record.pop(0)
        self.archived    = record.pop(0)
        self.fold        = record.pop(0)
        self.unread      = record.pop(0)
        self.ignore      = record.pop(0)

        self.obj = obj

        self.mail_map = {}
        self.mail_list = []

        self.tops = []
        self.left = []
        self.loaded = False

    def load_mails(self, mails = None):
        if mails == None:
            mails = db.index.filter(topic_id = self.id).select()

        for m in mails:
            msgid = m.Message_id()

            m.topic = self.obj

            l = self.mail_map.get(msgid)

            if not l:
                self.mail_map[msgid] = m
                self.mail_list.append(m)
                continue

            # handler for the same mail

            if l.mbox == 'Sent':
                if l.isnew:
                    l.mark_readed()
                self.mail_map[msgid] = m
                self.mail_list.remove(l)
                self.mail_list.append(m)

            else:
                if m.isnew:
                    m.mark_readed()
                self.left.append(m)

        self.mail_list.sort(key = lambda x: x.Date_ts())

    def find_upper(self, m):
        if m.parent or m in self.tops:
            return

        r = m.In_reply_to()
        msgid = m.Message_id()

        if not r or r == msgid:
            self.tops.append(m)
            return

        p = self.mail_map.get(r)
        if p:
            p.append(m)
            self.find_upper(p)
            return

        self.tops.append(m)

    def thread(self):
        for m in self.mail_list:
            self.find_upper(m)

        for m in self.tops:
            m.thread(0, m)


        self.tops.sort(key = lambda x: x.last_recv_ts())

class Topic(object):
    def __init__(self, mail, record = None):
        self.root = None
        self.tops = []

        self.marked_n = 0

        if mail:
            self.root = mail
            self.mbox = mail.mbox
            self.tops.append(mail)

        if record:
            self.db = TopicDb(record, self)
        else:
            self.db = None

    def loaded(self):
        return self.db.loaded

    def load(self, force = False, mails = None):
        if not force:
            if self.db.loaded:
                return

        self.db.loaded = True

        self.db.load_mails(mails)
        self.db.thread()

        if self.db.mail_list:
            self.root = self.db.mail_list[0]
        self.mbox = self.db.mbox

        self.check_update()

    def _check_update(self):
        if self.topic() != self.db.topic:
            return True

        if self.timestamp() != self.db.last_ts:
            return True

    def check_update(self):
        if not self._check_update():
            return

        db.topic.filter(id = self.db.id).update(
                topic    = self.topic(),
                last_ts  = self.timestamp(),
                mail_n   = len(self.db.mail_list),
                thread_n = len(self.db.tops))

        self.db.topic    = self.topic()
        self.db.last_ts  = self.timestamp()
        self.db.mail_n   = len(self.db.mail_list),
        self.db.thread_n = len(self.db.tops)

    def topic(self):
        if self.root:
            tp = self.root.Subject()
        else:
            tp = self.db.topic

        tp = tp.strip()
        if tp and tp[0] == '[':
            pos = tp.find(']')
            if pos == -1:
                pos = 0
            else:
                pos += 1
            tp = tp[pos:].strip()

        return tp

    def delete(self):
        db.topic.filter(id = self.db.id).delete()

    def set_archived(self):
        if self.db.archived:
            flag = 0
        else:
            flag = 1

        db.topic.filter(id = self.db.id).update(archived = flag)


    def timestamp(self):
        if self.tops:
            tops = self.tops

        elif self.db and self.db.loaded and self.db.tops:
            tops = self.db.tops
        else:
            return self.db.last_ts

        return max([x.last_recv_ts() for x in tops])

    def output(self, reverse = False):
        top = self.db.tops
        if reverse:
            top = top[::-1]

        o = []
        for m in top:
            m.output(o)

#        for m in self.db.left:
#            o.append(m)

        return o

    def merge(self, fr):
        topic_merge(self.db.id, fr)

    def get_id(self):
        return self.db.id

    def get_unread(self):
        return self.db.unread

    def get_threads(self):
        return self.db.tops

    # move topic to other mbox, such as move to the focus mbox,
    def set_mbox(self, mbox):
        """
            TODO 手动设置的 mbox 分类, 要增加标记, 这样不会在 refresh_class 的
            被删除掉.
        """
        db.topic.filter(id = self.db.id).update(mbox = mbox)
        self.mbox = mbox
        self.db.mbox = mbox

    def set_ignore(self):
        if self.db.ignore:
            v = 0
        else:
            v = 1

        db.topic.filter(id = self.db.id).update(ignore = v)
        self.db.ignore = v

    def get_ignore(self):
        return self.db.ignore

    def get_mbox(self):
        return self.db.mbox
