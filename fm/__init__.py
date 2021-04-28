# -*- coding:utf-8 -*-


import os
import time
from . import send
from . import syncmail
from . import conf
from . import mail
from . import mbox
from . import db

Mail = mail.Mail

conf = conf.conf

sendmail = send.sendmail
Mbox = mbox.Mbox

def boxes():
    return db.class_names.array

def unread_stats():
    return db.unread()

def unread_ev_bind(cb):
    db.class_names.bind_ev_unread(cb)

class g:
    msgid = 0

def gen_msgid():
    g.msgid += 1
    return "<%s-%s-%s>" % (time.time(), g.msgid, conf.me)


def last_check_ts():
    return conf.mailbox.last_check

# fm will been loaded by vim plugin, so
# init cannot happend when module load.
# setup should called before use for vim
def setup():
    db.setup()

try:
    import vim
except:
    setup()

