#!/bin/env python2
# -*- coding:utf-8 -*-

import json
import os
import sys

import imaplib
import email
import time
import subprocess
import transfermail


class config:
    confd = os.path.expanduser("~/.syncmail")
    server   = None
    port     = None
    user     = None
    password = None
    folders  = None
    deliver  = None
    saved    = False
    procmail = os.path.join(confd, 'procmail.py')
    transfer =  None

def conf():
    path = os.path.expanduser("~/.syncmailrc")
    c = open(path).read()
    j = json.loads(c)

    config.server   = j['server']
    config.port     = j['port']
    config.user     = j['user']
    config.password = j['password']
    config.folders = j['folders']
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


    config.current_total = data

    typ, [data] = conn.uid('search', None, 'ALL')
    ids = data.split()

    ii = 0;
    for i in ids:
        i = int(i)

        if i <= last:
            ii += 1
            continue

        break

    print("search %s. %s(%s). last: %s download: %s " % (typ, fold,
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
    open(t, 'w').write(uid)


def save_mail(dirname, mail, Id, uid):
    path = os.path.join(config.deliver, dirname)
    new = os.path.join(path, 'new')
    if not os.path.isdir(path):
        os.mkdir(path)
        t = os.path.join(path, 'tmp')
        os.mkdir(t)
        t = os.path.join(path, 'cur')
        os.mkdir(t)
        os.mkdir(new)

    filename = "%s-%s.eu6sqa" % (uid, time.time())

    path = os.path.join(new, filename)

    open(path, 'w').write(mail)
    save_uid(uid)
    config.saved = True

    m = email.message_from_string(mail)

    print("  [save %s/%s to %s] %s" % (
        Id,
        config.current_total,
        dirname,
        m.get("Subject", '').replace('\n', ' ')
        ))


def procmail(mail):
    cmd = ['python2', config.procmail]

    p = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate(mail)

    o = []
    for l in stdout.split('\n'):
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
        if mail == ')':
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




def main():
    conf()

    conn = imaplib.IMAP4_SSL(host = config.server, port = config.port)

    typ, [data] = conn.login(config.user, config.password)
    if typ != 'OK':
        print("login fail" % fold)
        return

    for fold in config.folders:
        config.current_fold = fold

        last = get_last_uid()

        sync(conn, fold, last, procmails)




import argparse
parser = argparse.ArgumentParser(description="sync mail")
parser.add_argument('-l', '--loop', help="loop", action='store_true')


args = parser.parse_args()

if args.loop:
    while True:
        t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        print("%s syncmail..." % t)

        try:
            main()
        except Exception as e:
            print e

        time.sleep(60)
else:
    main()
    if config.saved:
        sys.exit(1)
    else:
        sys.exit(0)


