#!/bin/env python2
# -*- coding:utf-8 -*-

import json
import os
import sys

import imaplib
import email
import time
import subprocess
from . import transfermail

from . import mail
from . import db

db = db.db

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

    print("")
    print(">> %-10s: search %s. total: %s. last: %s download: %s " % (fold, typ,
        config.current_total, last, len(ids) - ii))

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
    open(t, 'w').write(uid.decode('utf8'))

def save_last_check():
    t = os.path.join(config.confd, config.user)
    if not os.path.isdir(t):
        os.mkdir(t)

    path = os.path.join(t, 'last_check')
    open(path, 'w').write(str(time.time()))


def save_mail_to_db(path, mbox):
    m = mail.Mail(path)
    m.db_insert(mbox)

    r = m.In_reply_to()
    if not r:
        return

    db.sub_n_incr(r)
    db.commit()


def save_mail(dirname, mail, Id, uid):
    config.gid += 1

    filename = "%s-%s-%s.mail" % (uid, time.time(), config.gid)

    path = os.path.join(config.deliver, dirname)
    if not os.path.isdir(path):
        os.mkdir(path)

    path = os.path.join(path, filename)

    open(path, 'wb').write(mail)

    save_mail_to_db(path, dirname)

    save_uid(uid)
    config.saved = True

    m = email.message_from_bytes(mail)

    print("  [save %s/%s to %s] %s" % (
        int(Id),
        config.current_total,
        dirname,
        m.get("Subject", '').replace('\n', ' ').replace('\r', '')
        ))


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

                tfmail(mail, d)
                continue

            save_mail(d, mail, Id, uid)


def procmails_builin(maillist):
    for mail in maillist:
        if mail == ')':
            continue

        Id = mail[0].split()[0]
        uid = mail[0].split()[2]
        mail = mail[1]

        d = config.current_fold
        save_mail(d, mail, Id, uid)


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




