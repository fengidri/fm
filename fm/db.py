# -*- coding:utf-8 -*-
import sqlite3

import os

class Db(object):
    def __init__(self):
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


        cmd_table = '''CREATE TABLE IF NOT EXISTS FMIndex
                   (
                   status      INT  default 0,
                   mbox        TEXT NOT NULL,
                   sub_n       INT default 0,

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
                   fold        BOOL default 0
                   );'''

        r = c.execute(cmd_table)
        c.execute('CREATE INDEX IF NOT EXISTS mi ON FMIndex(msgid, mbox, in_reply_to);')
        c.execute("select count(*) From FMIndex")
        rows = c.fetchone()[0]
        if rows == 0:
            self.isempty = True
        else:
            self.isempty = False

        conn.commit()

    def _exec(self, cmd):
        if not self.conn:
            return

        try:
            return self.c.execute(cmd)
        except:
            print(cmd)
            raise(Exception(cmd))

    def commit(self):
        self.conn.commit()

    def insert_mail(self, mbox, m):
        cmd = '''insert into FMIndex ("mbox", "status", "sub_n",
                                      "subject", "date", "to", "from", "cc", "msgid", "in_reply_to",
                                      "attach_n", "size", "path")
                               values("{mbox}", {status}, {sub_n}, '{subject}',
                                      "{date}", '{to}', '{From}', '{cc}', "{msgid}",
                                      '{in_reply_to}', "{attach_n}", "{size}", "{path}")'''

        def h(s):
            if not s:
                return s
            return s.replace("'", "''").replace('\r', '').replace('\n', ' ')

        if m.isnew:
            status = 0
        else:
            status = 1

        cc = h(m.header('Cc'))
        to = h(m.header('to'))
        f = h(m.header('from'))
        sub = h(m.Subject())

        cmd = cmd.format(mbox = mbox,
                   sub_n       = m.sub_n,
                   subject     = sub,
                   status      = status,
                   date        = m.Date(),
                   to          = to,
                   From        = f,
                   cc          = cc,
                   msgid       = m.Message_id(),
                   in_reply_to = m.In_reply_to(),
                   attach_n    = len(m.Attachs()),
                   size        = m.size,
                   path        = m.path,
                   )
        return self._exec(cmd)

    def find_by_msgid(self, msgid):
        cmd = 'select *,rowid from FMIndex where msgid="%s"' % msgid
        self._exec(cmd)
        t = self.c.fetchone()
        if not t:
            return
        return t

    def find_by_reply(self, rid):
        cmd = 'select *,rowid from FMIndex where in_reply_to="%s" and mbox!="Sent"' % rid
        self._exec(cmd)
        return self.c.fetchall()

    def getall_mbox(self, mbox):
        cmd = 'select *,rowid from FMIndex where mbox="%s"' % mbox
        self._exec(cmd)
        return self.c.fetchall()

    def mark_readed(self, m):
        cmd = 'update FMIndex set status=1 where msgid="%s" ' % m.Message_id()
        ret = self._exec(cmd)
        self.conn.commit()
        return  ret

    def sub_n_incr(self, msgid):
        cmd = 'update FMIndex set sub_n=sub_n + 1 where msgid="%s"' %  msgid
        self._exec(cmd)
        self.conn.commit()
        return self.c.rowcount

    def sub_n_set(self, msgid, n):
        cmd = 'update FMIndex set sub_n=%s where msgid="%s"' %  (n, msgid)
        self._exec(cmd)
        self.conn.commit()
        return self.c.rowcount

    def set_fold(self, rowid, v):
        cmd = 'update FMIndex set fold=%s where rowid=%s' %  (v, rowid)
        self._exec(cmd)
        self.conn.commit()
        return self.c.rowcount

    def del_mail(self, mail):
        cmd = "delete from FMIndex where rowid=%s" % mail.rowid
        self._exec(cmd)
        self.conn.commit()
        return self.c.rowcount


db = Db()
