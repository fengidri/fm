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

class g:
    current_total = None
    gid           = 0
    saved         = False
    current_fold = None

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

def save_mail_to_db(path, mbox, delay = False):
    m = mail.Mail(path)
    m.isnew = True
    m.mbox = mbox # for topic

    # 查找 thread 相关的 mails
    mails = db.index.relative(m)
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

    db.topic.filter(id = topic_id).update(last_ts = m.Date_ts())

    db.commit()
    return rowid, topic_id


def save_mail(fold, dirname, mail, Id, uid):
    uid = uid.decode('utf8')
    Id = int(Id)

    g.gid += 1

    # save mail to file
    filename = "%s-%s-%s.mail" % (uid, time.time(), g.gid)

    path = os.path.join(conf.deliver, dirname)
    if not os.path.isdir(path):
        os.mkdir(path)

    path = os.path.join(path, filename)

    open(path, 'wb').write(mail)

    # save mail to db
    start = time.time()
    rowid, topic_id = save_mail_to_db(path, dirname)
    end = time.time()

    # save uid
    save_uid(uid)

    g.saved = True

    # for log
    m = email.message_from_bytes(mail)

    s = m.get("Subject", '').replace('\n', ' ').replace('\r', '')
    print("save %s:%s/%s to %s(rowid: %d topic_id: %d) %.3fs. %s" % (fold, Id,
        g.current_total, dirname, rowid, topic_id,  end - start, s))


def procmail(mail):
    cmd = ['python2', conf.procmail]

    p = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate(mail)

    o = []
    for l in stdout.decode('utf8').split('\n'):
        l = l.strip()
        if not l:
            continue

        o.append(l)

    return o


def procmails(fold, maillist):
    for mail in maillist:
        if mail == b')':
            continue

        Id = mail[0].split()[0]
        uid = mail[0].split()[2]
        mail = mail[1]

        ds = procmail(mail)
        for d in ds:
            if d[0] == '>':
                d = d[1:].strip()
                if not d:
                    continue

                continue

            save_mail(fold, d, mail, Id, uid)


def procmails_builin(fold, maillist):
    for mail in maillist:
        if mail == b')':
            continue

        Id = mail[0].split()[0]
        uid = mail[0].split()[2]
        mail = mail[1]

        d = g.current_fold
        save_mail(fold, d, mail, Id, uid)

def sync(conn, fold, last, callback):
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


def rebuild_db():
    start = time.time()
    i = 0

    def handle(path, d, i):
        if i % 500 == 0:
            print("process %d done. spent: %d" % (i, time.time() - start))

        save_mail_to_db(path, d, delay = True)


    dirs = os.listdir(conf.deliver)
    for d in dirs:
        if d[0] == '.':
            continue
        dirpath = os.path.join(conf.deliver, d)
        for f in os.listdir(dirpath):
            if f[0] == '.':
                continue

            path = os.path.join(dirpath, f)
            if os.path.isdir(path):
                for f in os.listdir(path):
                    npath = os.path.join(path, f)
                    i += 1
                    handle(npath, d, i)
            else:
                i += 1
                handle(path, d, i)

    db.commit() # for delay


    print("rebuild db spent: %d/%d" % (time.time() - start, i))


def main():
    conn = imaplib.IMAP4_SSL(host = conf.server, port = conf.port)

    while True:
        try:
            typ, [data] = conn.login(conf.user, conf.password)
            if typ != 'OK':
                print("login fail" % fold)
                return
            break
        except imaplib.error:
            time.sleep(5)
            continue

    for fold in conf.folders:
        g.current_fold = fold

        last = get_last_uid()

        sync(conn, fold, last, procmails)

    fold = 'Sent'
    g.current_fold = fold
    last = get_last_uid()
    sync(conn, fold, last, procmails_builin)

    save_last_check()




