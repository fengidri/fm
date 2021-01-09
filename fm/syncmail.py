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

class config:
    confd = os.path.expanduser("~/.fm.d")
    server   = None
    port     = None
    user     = None
    password = None
    folders  = None
    deliver  = None
    saved    = False
    procmail = os.path.join(confd, 'procmail.py')
    transfer =  None
    gid = 0

def conf():
    path = os.path.expanduser("~/.fm.json")
    c = open(path).read()
    j = json.loads(c)

    s = j['server']

    config.user     = j['user']

    config.server   = s['host']
    config.port     = s['port']
    config.password = s['password']
    config.folders =  s['folders']
    config.deliver = os.path.expanduser(j['deliver'])


    queue = get_dir('sendq')
    sent = get_dir('sent')
    config.transfer = transfermail.TransferMail(queue, sent)


def get_dir(name):
    path = os.path.join(config.confd, name)
    if not os.path.isdir(path):
        os.mkdir(path)

    return path


def sync(conn, fold, last, callback):
    typ, [data] = conn.select('"%s"' % fold)
    if typ != 'OK':
        print("select to folder: %s. fail" % fold)
        sys.exit(-1)


    config.current_total = data.decode('utf8')

    typ, [data] = conn.uid('search', None, 'ALL')
    ids = data.split()

    ii = 0;
    for i in ids:
        i = int(i)

        if i <= last:
            ii += 1
            continue

        break

    #print(">> %-10s: search %s. total: %s. last: %s download: %s " % (fold, typ,
    #    config.current_total, last, len(ids) - ii))

    for i in ids[ii:]:
        resp, data = conn.uid('fetch', i, '(RFC822)')
        callback(data)

def get_last_uid():
    fold = config.current_fold
    if not os.path.isdir(config.confd):
        return -1

    t = os.path.join(config.confd, config.user)
    if not os.path.isdir(t):
        return -1

    t = os.path.join(t, fold)
    if not os.path.isdir(t):
        return -1

    t = os.path.join(t, 'uid')
    if not os.path.isfile(t):
        return -1

    uid = open(t).read()
    return int(uid)


def save_uid(uid):
    fold = config.current_fold
    if not os.path.isdir(config.confd):
        os.mkdir(config.confd)

    t = os.path.join(config.confd, config.user)
    if not os.path.isdir(t):
        os.mkdir(t)

    t = os.path.join(t, fold)
    if not os.path.isdir(t):
        os.mkdir(t)

    t = os.path.join(t, 'uid')
    open(t, 'w').write(uid)

def save_last_check():
    t = os.path.join(config.confd, config.user)
    if not os.path.isdir(t):
        os.mkdir(t)

    path = os.path.join(t, 'last_check')
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
    db.set_delay()

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
        db.index.insert(m, mbox, topic_id)

        # 检查当前的 mbox 有没有对应的 topic
        if mbox != 'Sent':
            tps = db.topic.filter(id = topic_id, mbox = mbox).select()
            if len(tps) > 1:
                for tp in tps[1:]:
                    db.topic.delete(id = tp.db.id)
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

        db.index.insert(m, mbox, topic_id)

    if delay:
        return

    db.commit()


def save_mail(dirname, mail, Id, uid):
    uid = uid.decode('utf8')
    Id = int(Id)

    config.gid += 1

    # save mail to file
    filename = "%s-%s-%s.mail" % (uid, time.time(), config.gid)

    path = os.path.join(config.deliver, dirname)
    if not os.path.isdir(path):
        os.mkdir(path)

    path = os.path.join(path, filename)

    open(path, 'wb').write(mail)

    # save mail to db
    start = time.time()
    save_mail_to_db(path, dirname)
    end = time.time()

    # save uid
    save_uid(uid)

    config.saved = True

    # for log
    m = email.message_from_bytes(mail)

    s = m.get("Subject", '').replace('\n', ' ').replace('\r', '')
    print("  [save %s/%s to %s] %s. -- %s" % (Id, config.current_total, dirname, s, end - start))


def procmail(mail):
    cmd = ['python2', config.procmail]

    p = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate(mail)

    o = []
    for l in stdout.decode('utf8').split('\n'):
        l = l.strip()
        if not l:
            continue

        o.append(l)

    return o

def tfmail(mail, d):
    m = email.message_from_string(mail)
    m.add_header("Resent-To", d)

    mail = m.as_string()

    config.transfer.append(mail)


def procmails(maillist):
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

    #            tfmail(mail, d)
                continue

            save_mail(d, mail, Id, uid)


def procmails_builin(maillist):
    for mail in maillist:
        if mail == b')':
            continue

        Id = mail[0].split()[0]
        uid = mail[0].split()[2]
        mail = mail[1]

        d = config.current_fold
        save_mail(d, mail, Id, uid)

def rebuild_db():
    conf()

    start = time.time()
    i = 0

    def handle(path, d, i):
        if i % 500 == 0:
            print("process %d done. spent: %d" % (i, time.time() - start))

        save_mail_to_db(path, d, delay = True)


    dirs = os.listdir(config.deliver)
    for d in dirs:
        if d[0] == '.':
            continue
        dirpath = os.path.join(config.deliver, d)
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
    conf()

    conn = imaplib.IMAP4_SSL(host = config.server, port = config.port)
    print("Mail: %s" % config.user)

    typ, [data] = conn.login(config.user, config.password)
    if typ != 'OK':
        print("login fail" % fold)
        return

    for fold in config.folders:
        config.current_fold = fold

        last = get_last_uid()

        sync(conn, fold, last, procmails)

    fold = 'Sent'
    config.current_fold = fold
    last = get_last_uid()
    sync(conn, fold, last, procmails_builin)

    save_last_check()




