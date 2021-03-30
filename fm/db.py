# -*- coding:utf-8 -*-
import sqlite3

import os
from . import mail
from . import topic as topic_module
from . import db_driver

class_sql = '''
CREATE TABLE IF NOT EXISTS FMClass
(
    mbox        TEXT NOT NULL,
    sort        INT default 100000,
    unique(mbox)
);
'''

index_sql = '''
CREATE TABLE IF NOT EXISTS FMIndex
(
    status      INT  default 0,
    mbox        INT default 0,

    "Subject"     TEXT NOT NULL,
    "Date"        TEXT NOT NULL,
    "To"          TEXT NOT NULL,
    "From"        TEXT NOT NULL,
    "Cc"          TEXT NOT NULL,

    "Msgid"       TEXT NOT NULL,
    "In_reply_to" TEXT NOT NULL,

    attach_n    TEXT NOT NULL,
    size        INT  default 0,
    path        TEXT NOT NULL,
    fold        BOOL default 0,
    flag        INT  default 0,
    ts          INT  default 0,
    miss_upper  BOOL default 0,
    topic_id    INT default 0
);
'''
index_sql0 = 'CREATE INDEX IF NOT EXISTS fmindex_topic_id ON FMIndex(topic_id);'
index_sql1 = 'CREATE INDEX IF NOT EXISTS fmindex_msgid ON FMIndex(msgid);'
index_sql2 = 'CREATE INDEX IF NOT EXISTS fmindex_irt ON FMIndex(in_reply_to);'
index_sql3 = 'CREATE INDEX IF NOT EXISTS fmindex_status ON FMIndex(status);'

topic_sql = '''
CREATE TABLE IF NOT EXISTS FMTopic
(
    id    INT  default 0,

    topic       TEXT NOT     NULL,
    mbox        INT default 0,

    first_ts    INT  default 0,
    last_ts     INT  default 0,

    sponsor     TEXT NOT     NULL,
    participant TEXT NOT     NULL,

    mail_n      INT  default 0,
    thread_n    INT  default 0,
    archived    INT  default 0
);
'''
topic_sql1 = 'CREATE INDEX IF NOT EXISTS ti ON FMTopic(mbox);'


class Db(db_driver.DB):
    def __init__(self):
        db_driver.DB.__init__(self)

        path = '~/.fm.d/db/index.db'
        path = os.path.expanduser(path)
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        path = os.path.expanduser(path)

        conn = sqlite3.connect(path)

        c = conn.cursor()
        self.conn = conn
        self.c = c

        c = conn.cursor()

        c.execute(class_sql)

        c.execute(index_sql)
        c.execute(index_sql0)
        c.execute(index_sql1)
        c.execute(index_sql2)
        c.execute(index_sql3)

        c.execute(topic_sql)
        c.execute(topic_sql1)

        conn.commit()

class ClassNames(db_driver.Table):
    def __init__(self):
        self.table = 'FMClass'
        self.db = db
        self.update()

        self.unread = {}
        # unread status
        cmd = "select mbox,count(*) from FMIndex where status=0 group by mbox;"
        self.db._exec(cmd)
        stats = self.db.c.fetchall()
        for mboxid, c in stats:
            mboxname = self.getname(mboxid)
            self.unread[mboxname] = c

    def update(self):
        self.ids = {}
        self.names = {}
        self.array = []

        rows = self.filter().select()

        rows.sort(key = lambda x: x[2])

        for _id, name, sort in rows:
            self.array.append(name)
            self.ids[_id] = name
            self.names[name] = _id

    def getid(self, name):
        if name in self.names:
            return self.names[name]

        sql = db_driver.SqlFormat()
        sql.mbox = name
        cmd = sql.insert_format(self.table)

        db._exec(cmd)
        self.db.conn.commit()

        self.update()

        return self.names[name]


    def getname(self, _id):
        if _id in self.ids:
            return self.ids[_id]

class Topic(db_driver.Table):
    def __init__(self):
        self.table = 'FMTopic'
        self.db = db

    def insert(self, topic, id = None):
        sql = db_driver.SqlFormat()

        sql.topic       = topic.topic()
        sql.mbox        = class_names.getid(topic.mbox)
        sql.last_ts     = topic.timestamp()
        sql.first_ts    = topic.timestamp()
        sql.sponsor     = ''
        sql.participant = ''
        sql.mail_n      = 0
        sql.thread_n    = 0

        if id:
            sql.id = id

        cmd = sql.insert_format(self.table)

        db._exec(cmd)
        self.db.conn.commit()

        if id == None:
            rowid = self.db.last_rowid()

            self.filter(rowid = rowid).update(id = rowid)

            return rowid
        else:
            return id

    def sel_handle(self, ret):
        ms = []
        for r in ret:
            t = topic_module.Topic(None, record = r)
            ms.append(t)
        return ms

    # for filter/update rewrite kv
    def kv_handle(self, key, value):
        if key == 'mbox':
            return key, class_names.getid(value)
        return key, value


class Index(db_driver.Table):
    def __init__(self):
        self.table = 'FMIndex'
        self.db = db

    def fetch_mail(self, cmd):
        self.db._exec(cmd)
        ms = []
        for m in self.db.c.fetchall():
            m = MailFromDb(m)
            ms.append(m)
        return ms

    def sel_handle(self, ret):
        ms = []
        for m in ret:
            m = MailFromDb(m)
            ms.append(m)
        return ms

    # for filter/update rewrite kv
    def kv_handle(self, key, value):
        if key == 'mbox':
            return key, class_names.getid(value)
        return key, value

    def relative(self, mail):
        r = mail.In_reply_to()
        i = mail.Message_id()

        if r and i:
            f1 = self.filter(in_reply_to = i)
            f2 = self.filter(msgid = r)
            f = f1 + f2
            return f.select()

        elif r:
            return self.filter(msgid = r).select()

        elif i:
            return self.filter(in_reply_to = i).select()

        else:
            return []

    def batch_load_topics(self, topics):
        sql = []
        sql.append('select rowid,* from FMIndex where ')

        for topic in topics:
            sql.append(' topic_id=%s ' % topic.db.id)
            sql.append(' or ')

        sql = ''.join(sql[0:-1])
        self.db._exec(sql)

        return self.fetch_mail(sql)

    def insert(self, m, mbox, topic_id):
        sql = db_driver.SqlFormat()

        def h(s):
            if not s:
                return ''
            return s.replace('\r', '').replace('\n', ' ')

        if m.isnew:
            status = 0
        else:
            status = 1

        cc  = h(m.header('Cc'))
        to  = h(m.header('to'))
        f   = h(m.header('from'))
        sub = h(m.Subject())

        sql.mbox        = class_names.getid(mbox)
        sql.subject     = sub
        sql.status      = status
        sql.date        = m.Date()
        sql.to          = to
        sql.From        = f
        sql.cc          = cc
        sql.msgid       = m.Message_id()
        sql.in_reply_to = m.In_reply_to()
        sql.attach_n    = len(m.Attachs())
        sql.size        = m.size
        sql.path        = m.path
        sql.ts          = m.Date_ts()
        sql.topic_id    = topic_id

        cmd = sql.insert_format('FMIndex')

        db._exec(cmd)
        self.db.conn.commit()
        return self.db.last_rowid()


def commit():
    db.commit()

def set_delay():
    db.set_delay()

def setup():
    global db
    global topic
    global index
    global class_names

    db = Db()

    topic = Topic()
    index = Index()
    class_names = ClassNames()

class MailFromDb(mail.M):
    def __init__(self, record):
        mail.M.__init__(self)

        record = list(record)

        self.rowid       = record.pop(0)
        self.status      = record.pop(0)
        self.mbox        = class_names.getname(record.pop(0))
        self.subject     = record.pop(0)
        self.date        = record.pop(0)
        self.to          = record.pop(0)
        self._from       = record.pop(0)
        self.cc          = record.pop(0)
        self.msgid       = record.pop(0)
        self.in_reply_to = record.pop(0)
        self.attach_n    = record.pop(0)
        self.size        = record.pop(0)
        self.path        = record.pop(0)
        self.fold        = record.pop(0)
        self.flag        = record.pop(0)
        self.ts          = record.pop(0)
        self.miss_upper  = record.pop(0)
        self.topic_id    = record.pop(0)

        self.index = 0

        if self.status == 0:
            self.isnew = True

    def Subject(self):
        return self.subject

    def In_reply_to(self):
        return self.in_reply_to

    def Message_id(self):
        return self.msgid

    def Date(self):
        return self.date

    def From(self, real = False):
        if real:
            return self.real_header('From')[0]
        l = mail.EmailAddrLine(self._from)
        if l:
            return l[0]
        return mail.EmailAddr('')

    def To(self, real = False):
        if real:
            return self.real_header('To')
        return mail.EmailAddrLine(self.to)

    def Cc(self, real = False):
        if real:
            return self.real_header('Cc')
        return mail.EmailAddrLine(self.cc)

    def Date_ts(self):
        return self.ts

    def delete(self):
        index.filter(rowid = self.rowid).delete()

    def set_fold(self, v = None):
        if v == True:
            fold = 1
            self.fold = True

        if v == False:
            fold = 0
            self.fold = False

        if v == None:
            if self.fold:
                fold = 0
                self.fold = False
            else:
                fold = 1
                self.fold = True

        index.filter(rowid = self.rowid).update(fold = fold)

    def set_flag(self, flag):
        index.filter(rowid = self.rowid).update(flag = flag)
































