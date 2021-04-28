#!/bin/env python2
# -*- coding:utf-8 -*-

import json
import os
import sys

from collections import defaultdict

import imaplib
import email
import time
import subprocess
from . import transfermail

from . import mail
from . import topic
from . import db
from . import conf

conf = conf.conf

sys.path.insert(0, os.path.dirname(conf.procmail))

import procmail as _procmail


class g:
    current_total = None
    gid           = 0
    saved         = False
    current_fold = None
    builin = False

def get_path(*ns):
    ns = list(ns)
    ns.insert(0, conf.confd)

    root = None

    for n in ns[0:-1]:
        if root:
            n = os.path.join(root, n)

        if not os.path.isdir(n):
            os.mkdir()

        root = n

    return os.path.join(root, ns[-1])

def get_last_uid():
    path = get_path(conf.user, g.current_fold, 'uid')

    if not os.path.isfile(path):
        return -1

    uid = open(path).read()
    return int(uid)


def save_uid(uid):
    path = get_path(conf.user, g.current_fold, 'uid')

    open(path, 'w').write(uid)

def save_last_check():
    path = get_path(conf.user, 'last_check')
    open(path, 'w').write(str(time.time()))



def check_topic_need_merge(tp, mbox):
    rets = db.topic.filter(topic = tp.topic(), mbox = mbox).select()
    if rets:
        topic_id = rets[0].db.id

        if len(rets) > 1:
            fr = []
            for r in rets[1:]:
                fr.append(r.db.id)

            topic.topic_merge(topic_id, fr)
        return topic_id

def check_mail_need_merge(mails):
    topic_id = mails[0].topic_id

    fr = []
    for m in mails[1:]:
        if m.topic_id != topic_id:
            fr.append(m.topic_id)

    if not fr:
        return topic_id

    topic.topic_merge(topic_id, fr)
    return topic_id

def save_mail_to_db(m, mbox, delay = False):
    m.isnew = True
    m.mbox = mbox # for topic

    # 查找 thread 相关的 mails
    mails = db.index.relative(m)

    s = time.time()
    if mails:

        # 合并 thread 到一个 topic id
        # 可能有多个 topic, 但是 topic id 是一样的
        topic_id = check_mail_need_merge(mails)

        # 新邮件也使用这个 topic_id
        rowid = db.index.insert(m, mbox, topic_id)

        # 检查当前的 mbox 有没有对应的 topic
        if mbox != 'Sent':
            tps = db.topic.filter(id = topic_id, mbox = mbox).select()
            if len(tps) > 1:
                for tp in tps[1:]:
                    db.topic.filter(id = tp.db.id).delete()
            elif len(tps) == 0:
                tp = topic.Topic(m)
                db.topic.insert(tp, id = topic_id)

    else:
        # 创建 topic
        tp = topic.Topic(m)

        # 检查有没有相同 topic name 的 topic
        # 大于 1个就合并成一个
        topic_id = check_topic_need_merge(tp, mbox)
        if not topic_id:
            topic_id = db.topic.insert(tp)

        rowid = db.index.insert(m, mbox, topic_id)

    """
        注意: 这里可能是多个不同 mbox 但 id 相同的 topic
    """
    db.topic.filter(id = topic_id).update(last_ts = m.Date_ts(), archived = 0)

    db.commit()
    return rowid, topic_id

def save_mail_file(mail, uid, dirname = None):
    g.gid += 1
    filename = "%s-%s-%s.mail" % (uid, time.time(), g.gid)

    path = conf.deliver

    if dirname: # for builin
        path = os.path.join(path, dirname)

    path = os.path.join(path, filename)

    open(path, 'wb').write(mail)
    return path


def save_mail(fold, d, m, Id, start):

    rowid, topic_id = save_mail_to_db(m, d)
    end = time.time()

    # save uid

    g.saved = True

    # for log
    s = m.Subject()

    date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    print("%s save %s:%s/%s to %s(rowid: %d topic_id: %d) %.3fs. %s" % (date,
        fold, Id, g.current_total, d, rowid, topic_id,  end - start, s))


def procmail(mail):
    ds =  _procmail.procmail(mail)
    return ds

def procone(fold, Id, uid, msg):
    s = time.time()


    if g.builin:
        path = save_mail_file(msg, uid, g.current_fold)
        ds = [g.current_fold]
        m = None
    else:
        path = save_mail_file(msg, uid)
        m = mail.Mail(path)
        ds = procmail(m)

    for d in ds:
        if d[0] == '>':
            d = d[1:].strip()
            if not d:
                continue

            continue

        if not m:
            m = mail.Mail(path)

        save_mail(fold, d, m, Id, s)
        m = None

    save_uid(uid)

def procmails(fold, maillist):
    for raw in maillist:
        if raw == b')':
            continue

        Id = raw[0].split()[0]
        uid = raw[0].split()[2]

        procone(fold, int(Id), uid.decode('utf8'), raw[1])

def do(conn, fold, last, callback, builin = False):
    g.builin = builin

    typ, [data] = conn.select('"%s"' % fold)
    if typ != 'OK':
        print("select to folder: %s. fail" % fold)
        sys.exit(-1)


    g.current_total = data.decode('utf8')

    typ, [data] = conn.uid('search', None, 'ALL')
    ids = data.split()

    ii = 0;
    for i in ids:
        i = int(i)

        if i <= last:
            ii += 1
            continue

        break


    for i in ids[ii:]:
        resp, data = conn.uid('fetch', i, '(RFC822)')
        callback(fold, data)

def check_class(topics, mbox_ignore):
    mbox_new = []
    mbox_old = []

    topic_id = topics[0].get_id()
    for tp in topics:
        mbox_old.append(tp.get_mbox())

    mails = db.index.filter(topic_id = topic_id).select()
    for m in mails:
        ds = procmail(m)
        mbox_new.extend(ds)

    mbox_new = set(mbox_new)
    # 创建新的分类(mbox)对应的 topic 纪录
    for mbox in mbox_new:
        if mbox not in mbox_old:
            print("create new topic [%s] %s" % (mbox, topics[0].topic()))
            topic.topic_dup(topics[0], mbox)

    # 删除旧的分类(mbox)对应的 topic 纪录
    for mbox in mbox_old:
        if mbox in mbox_ignore:
            continue

        if mbox in mbox_new:
            continue

        print("delete topic [%s] %s" % (mbox, topics[0].topic()))

        db.topic.filter(id = topic_id, mbox = mbox).delete()

def refresh_class(mbox_ignore):
    # 对于所有的已经在数据库里面的邮件基于 procmail 进行重新分类

    """
    mbox 的管理方式参考, db 里面 topic 表的设计
    """
    topics = defaultdict(list)

    # 聚合相同 topic_id 的 topic
    for t in db.topic.filter().select():
        topics[t.get_id()].append(t)

    for tps in topics.values():
        check_class(tps, mbox_ignore)


def input(path):
    m = mail.Mail(path)

    ds = procmail(m)

    for d in ds:
        save_mail_to_db(m, d)
        print("save mail(%s) %s to mbox %s" % (path, m.Subject(), d))

class Rebuild(object):
    def walk_mail_file(self, handle):
        dirs = os.listdir(conf.deliver)
        for d in dirs:
            if d[0] == '.':
                continue

            dirpath = os.path.join(conf.deliver, d)

            if not os.path.isdir(dirpath):
                handle(dirpath, None)
                continue

            for f in os.listdir(dirpath):
                if f[0] == '.':
                    continue

                path = os.path.join(dirpath, f)
                if os.path.isdir(path):
                    for f in os.listdir(path):
                        npath = os.path.join(path, f)
                        handle(npath, d)
                else:
                    handle(path, d)

    def handle_mail(self, path, d):
        self.i += 1
        if self.i % 500 == 0:
            print("process %d/%d done. spent: %d from start" % (self.i,
                self.total, time.time() - self.start))

        m = mail.Mail(path)

        if d == 'Sent':
            ds = procmail(m)
        else:
            ds = procmail(m)

        for d in ds:
            save_mail_to_db(m, d, delay = True)

    def handle_sum(self, path, d):
        self.total += 1

    def __init__(self):
        self.i = 0
        self.total = 0
        self.start = time.time()

        self.walk_mail_file(self.handle_sum)
        self.walk_mail_file(self.handle_mail)

        db.commit() # for delay

        print("rebuild db spent: %d/%d" % (time.time() - self.start, self.i))


def sync():
    conn = imaplib.IMAP4_SSL(host = conf.server, port = conf.port)

    while True:
        try:
            typ, [data] = conn.login(conf.user, conf.password)
            if typ != 'OK':
                print("login fail" % fold)
                return
            break
        except:
            time.sleep(5)
            continue

    if os.path.isfile(conf.synclock):
        print("%s locked" % conf.synclock)
        return

    open(conf.synclock, 'w').close()

    for fold in conf.folders:
        g.current_fold = fold

        last = get_last_uid()

        do(conn, fold, last, procmails)

    fold = 'Sent'
    g.current_fold = fold
    last = get_last_uid()
    do(conn, fold, last, procmails, builin = True)

    save_last_check()

    os.remove(conf.synclock)



