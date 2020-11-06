# -*- coding:utf-8 -*-


import os
import email
import email.utils
import datetime
import time
import json
from email.header import decode_header
import subprocess
import sqlite3

class g:
    db = None

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
        else:
            self.alias = None
            self.addr = addr

        if '@' in self.addr:
            self.name, self.server = self.addr.split('@')
        else:
            self.name = self.addr
            self.server = ''

        if self.addr == conf.me:
            self.short = ''
        else:
            if self.alias:
                self.short = self.alias
            else:
                self.short = self.name

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
                   path        TEXT NOT NULL
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

        return self.c.execute(cmd)

    def mark_db(self, path):
        if path.endswith('.db'):
            return path

        npath =  path + '.db'

        os.rename(path, npath)
        return npath

    def commit(self):
        self.conn.commit()

    def insert_mail(self, mbox, m):
        cmd = '''insert into FMIndex ("mbox", "status", "sub_n",
                                      "subject", "date", "to", "from", "cc", "msgid", "in_reply_to",
                                      "attach_n", "size", "path")
                               values("{mbox}", {status}, {sub_n}, '{subject}',
                                      "{date}", '{to}', '{From}', '{cc}', "{msgid}",
                                      '{in_reply_to}', "{attach_n}", "{size}", "{path}")'''

        if m.isnew:
            status = 0
        else:
            status = 1

        cc = m.Cc()
        if cc:
            cc = cc.replace("'", "''")

        cmd = cmd.format(mbox = mbox,
                   sub_n       = m.sub_n,
                   subject     = m.Subject().replace("'", "''"),
                   status      = status,
                   date        = m.Date(),
                   to          = m.To().replace("'", "''"),
                   From        = m.From().replace("'", "''"),
                   cc          = cc,
                   msgid       = m.Message_id(),
                   in_reply_to = m.In_reply_to().replace("'", "''"),
                   attach_n    = len(m.Attachs()),
                   size        = m.size,
                   path        = m.path,
                   )
        return self._exec(cmd)

    def find_by_msgid(self, msgid):
        cmd = 'select * from FMIndex where msgid="%s"' % msgid
        self._exec(cmd)
        t = self.c.fetchone()
        if not t:
            return
        return t

    def find_by_reply(self, rid):
        cmd = 'select * from FMIndex where in_reply_to="%s"' % rid
        self._exec(cmd)
        return self.c.fetchall()

    def getall_mbox(self, mbox):
        cmd = 'select * from FMIndex where mbox="%s"' % mbox
        self._exec(cmd)
        return self.c.fetchall()

    def mark_readed(self, m):
        cmd = 'update FMIndex set status=1, path="%s" where msgid="%s" ' % (m.path, m.Message_id())
        ret = self._exec(cmd)
        self.conn.commit()
        return  ret

    def sub_n_incr(self, msgid):
        cmd = 'update FMIndex set sub_n=sub_n + 1 where msgid="%s"' %  msgid
        self._exec(cmd)
        self.conn.commit()
        return self.c.rowcount

class M(object):
    def __init__(self):
        self.sub_n = None
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


    def Body(self):
        b = self.get_mail()

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

    def header(self, header):
        h = self.get_mail().get(header)
        return decode(h)

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

    def mark_readed(self):
        name = os.path.basename(self.path)

        cur = os.path.dirname(self.path)
        cur = os.path.dirname(cur)
        cur = os.path.join(cur, 'cur')
        cur = os.path.join(cur, name)

        os.rename(self.path, cur)
        self.path = cur

        self.isnew = False
        g.db.mark_readed(self)


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

    def check_sub_n(self):
        if not self.sub_n:
            return

        if self.sub_n == len(self.sub_thread):
            return

        for r in g.db.find_by_reply(self.Message_id()):
            r = MailDb(r)
            for m  in self.sub_thread:
                if m.Message_id() == r.Message_id():
                    break
            else:
                self.append(r)

    def thread(self, index, head):
        self.index = index

        self.thread_head = head

        self.check_sub_n()

        if not self.sub_thread:
            return

        self.sub_thread.sort(key = lambda x: x.Date_ts())
        self.sub_thread[0].isfirst = True
        self.sub_thread[-1].islast = True

        for m in self.sub_thread:
            m.thread(index + 1, head)


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




# this init from file path
class Mail(M):
    def __init__(self, path):
        M.__init__(self)
        self.path = path

    def Subject(self):
        s = self.header('Subject')

        return s.replace('\n', '').replace('\r', '')

    def In_reply_to(self):
        if not self.header_in_reply_to:
            r = self.get_mail().get("In-Reply-To", '')
            r = r.split('\n')[0].strip()
            self.header_in_reply_to = r

        return self.header_in_reply_to

    def Message_id(self):
        if not self.header_message_id:
            self.header_message_id = self.get_mail().get("Message-Id", '').strip()

        return self.header_message_id

    def Date(self):
        d= self.get_mail().get("Date")
        if not d:
            d = 'Mon, 01 Jul 1979 00:00:00 +0800'
        return d

    def From(self):
        return self.get_mail().get('From')

    def To(self):
        return self.get_mail().get("TO")

    def Cc(self):
        return self.get_mail().get("Cc")

    def Date_ts(self):
        d = email.utils.parsedate_tz(self.Date())
        return email.utils.mktime_tz(d)

    def db_insert(self, mbox):
        self.path = g.db.mark_db(self.path)
        g.db.insert_mail(mbox, self)



class MailDb(M):
    def __init__(self, record):
        M.__init__(self)

        self.status      = record[0]
        self.mbox        = record[1]
        self.sub_n       = record[2]
        self.subject     = record[3]
        self.date        = record[4]
        self.to          = record[5]
        self._from        = record[6]
        self.cc          = record[7]
        self.msgid       = record[8]
        self.in_reply_to = record[9]
        self.attach_n    = record[10]
        self.size        = record[11]
        self.path        = record[12]

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

    def From(self):
        return self._from

    def To(self):
        return self.to

    def Cc(self):
        return self.cc

    def Date_ts(self):
        d = email.utils.parsedate_tz(self.Date())
        return email.utils.mktime_tz(d)


class Mbox(object):
    def __init__(self, dirname):
        self.top = []
        self.mail_map = {}
        self.mail_list = []

        self.mbox = os.path.basename(dirname)

        self.load_db()

        self.thread()

        g.db.commit()


    def load_db(self):
        for r in g.db.getall_mbox(self.mbox):
            m = MailDb(r)
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

                t = g.db.find_by_msgid(r)
                if t:
                    t = MailDb(t)
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

def sendmail(path):
    c = open(path).read()
    c = bytes(c, encode='utf8')
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
        self.deliver = p

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


def load_dir_to_db(path, mbox, isnew, pmaps):
    for f in os.listdir(path):

        if not g.db.isempty and f.endswith('.db'):
            continue

        f = os.path.join(path, f)

        m = Mail(f)
        m.isnew = isnew
        m.sub_n = pmaps.get(m.Message_id(), 0)
        m.db_insert(mbox)

        r = m.In_reply_to()
        if not r:
            continue

        n = g.db.sub_n_incr(r)
        if n:
            continue

        if pmaps.get(r):
            pmaps[r] += 1
        else:
            pmaps[r] = 1

def load_to_db():
    pmaps = {}

    for mbox in conf.mbox:
        dirname = mbox['path']
        name = mbox['name']
        new = os.path.join(dirname, 'new')
        cur = os.path.join(dirname, 'cur')
        load_dir_to_db(new, name, True, pmaps)
        load_dir_to_db(cur, name, False, pmaps)

    g.db.commit()


def init():
    global conf

    conf = Conf()
    g.db = Db()
    load_to_db()


if __name__ == '__main__':
    import sys
    init()
    if len(sys.argv) > 1:
        path = sys.argv[1]
        m = Mail(path)
        print(m.Body())

    else:
        print(conf.mbox)

        mbox = Mbox(conf.mbox[3]['path'])
        head = None
        for m in mbox.output():
            if m.thread_head != head:
                print('')
                head = m.thread_head

            print("%s" % (m.str(), ))



