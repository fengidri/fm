# -*- coding:utf-8 -*-

import pyvim
import vim

from frainui import LIST
import frainui
from pyvim import log as logging
import time
import email
import email.utils
import os

import subprocess
import datetime
import sys

import fm
import g
import mpage

def need_hide_subject(m):
    m.hide_subject = False

    subject = m.Subject()
    if m.index > 0:
        if subject[0:3].lower() == 're:':
            if subject[4:] == g.last_subject:
                m.hide_subject = True
                return
        else:
            if subject == g.last_subject:
                m.hide_subject = True
                return

    g.last_subject = subject



class MailList(object):
    def __init__(self):
        ui_list = LIST("FM List", self.list_handler, ft='fmindex',
                use_current_buffer = True, title = 'FM List')

        self.ui_list = ui_list

        g.ui_list = ui_list

    def refresh(self):
        pos = vim.current.window.cursor

        g.ui_list.show()
        g.ui_list.refresh()

        vim.current.window.cursor = pos

    def strdate(self, m):
        date = m.Date_ts()
        if g.config_relative_time:
            if not m.parent:
                date = time.strftime("%m-%d %H:%M", time.localtime(date))
            else:
                f = time.localtime(m.thread_head.Date_ts())
                d = time.localtime(date)
                hm = time.strftime("%H:%M", d)

                f1 = datetime.datetime(f.tm_year, f.tm_mon, f.tm_mday)
                d1 = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday)

                day = (d1 - f1).days

                if day:
                    date = '+%d %s' % (day, hm)
                else:
                    date = hm

                date = date.rjust(len('01-01 00:00'))



        elif g.config_short_time:
            now = time.time()
            s = time.strftime("%m-%d %H:%M", time.localtime(date))
            d = time.strftime('%m-%d ', time.localtime())
            if s.startswith(d):
                n = len(d)
                date = ' ' * n + s[n:]
            else:
                date = s
        else:
            date = time.strftime("%m-%d %H:%M", time.localtime(date))

        return date

    def strline1(self, m, head = None):
        if m.isnew:
            stat = '*'
        else:
            stat = ' '

        if m.flag:
            stat += '⚑'
        else:
            stat += ' '

        date = self.strdate(m)
        f = ''

        if m.is_reply():
            f = m.From().short
            if f != '':
                f = '%s' % f

            if f:
                f = '%s' % f
            else:
                f = 'Me'

            subject = f
            follow_from = False
        else:
            subject =  m.Subject().strip()
            follow_from = True

        if m.parent:
            i1 = m.parent.index * '|   '
            prefix = '%s|---' %(i1, )
            subject = prefix + subject

        if m.fold:
            subject += ' ......'

        l = 90
        if follow_from:
            l -= len(m.From().short) + 4

        subject = subject.ljust(l)[0:l]

        if follow_from:
            subject += '    '
            subject += m.From().short

        ext = ''
        if m == head:
            ext += ' (%d)' % m.num()

        if g.exts:
            fmt = '{stat} {subject} {date} {ext} {mbox} {rowid} {topic_id}'
        else:
            fmt = '{stat} {subject} {date}'
        return fmt.format(stat = stat,
                subject = subject,
                _from = f,
                date = date, ext = ext, mbox = m.mbox, rowid = m.rowid,
                topic_id=m.topic_id);

    def strline(self, m, head = None):
        return self.strline1(m, head)
        if m.isnew:
            stat = '*'
        else:
            stat = ' '

        date = self.strdate(m)

        f = m.From().short
        if f != '':
            f = '%s' % f

#        f = f.rjust(15)[0:15]
        if f:
            f = '%s:' % f
        else:
            f = 'Me:'


        f = '%s %s' % (m.thread_prefix(fm.conf.me), f)

        f = f.ljust(30)[0:30]

        if m.hide_subject:
            subject = ''
        else:
            subject = m.Subject().strip()

#        subject = '%s %s %s' % (m.thread_prefix(fm.conf.me), f, subject)
        if m.fold:
            subject += ' ......'

        subject = subject.ljust(90)[0:90]

        ext = ''
        if m == head:
            ext += ' (%d)' % m.num()

        fmt = '{stat} {subject} {_from} {date}'
        fmt = '{stat}{_from} {subject} {date} {ext}'
        return fmt.format(stat = stat,
                subject = subject,
                _from = f,
                date = date, ext = ext);

    def mail_show(self, leaf, listwin):
        mail = leaf.ctx

        if mail.isnew:
            mail.mark_readed()

            leaf.update(self.strline(mail))

        mpage.show(mail)

        g.pager_buf = vim.current.buffer
        g.pager_mail = mail

    def topic_list(self, node, listwin):
        topic = node.ctx
        topic.load()

        g.topic_opend.append(topic.get_id())

        ms = topic.output(reverse=True)

        leaf_num = 0

        head = None
        for m in ms:
            first = False
            if head:
                if head != m.thread_head:
                    first = True
                    #if leaf_num > 1:
                    #    node.append(frainui.Leaf('', None, None))
                    node.append(frainui.Leaf('', None, None))

                    head = m.thread_head
            else:
                head = m.thread_head
                first = True

            if first:
                leaf_num = 0
            else:
                if head.fold and head.news() == 0:
                    continue

            need_hide_subject(m)

            s = self.strline(m, head)

            name = os.path.basename(m.path)

            l = frainui.Leaf(name, m, self.mail_show, display = s, last_win=True)
            leaf_num += 1
            node.append(l)

        node.append(frainui.Leaf('', None, None))


    def list_thread(self, mbox, node):
        topics = mbox.get_topics()

        for topic in topics:
            if topic.loaded():
                defopen = True
            else:
                defopen = False
                if topic.get_id() in g.topic_opend:
                    defopen = True

            if topic.get_id() in g.stash:
                prefix = ' @'
            else:
                prefix = ' '

            line = prefix + topic.topic()

            if g.exts:
                e = ' id: %d' % topic.get_id()
                line += e

            n = frainui.Node(line, topic, self.topic_list, isdir = False, defopen = defopen)

            node.append(n)

        self.ui_list.title = "MBox: %s topic: %s stash: %s" % (
                g.mbox['name'], len(topics), len(g.stash))

    def list_plain(self, mbox, node):
        ms = mbox.output(reverse=True)
        self.ui_list.title = "MBox: %s num: %s" % (g.mbox['name'], len(ms))

        head = None
        node.append(frainui.Leaf('', None, None))

        for m in ms:
            s = self.strline(m)

            name = os.path.basename(m.path)

            l = frainui.Leaf(name, m, self.mail_show, display = s, last_win=True)
            node.append(l)

    def list_handler(self, node, listwin):
        mbox = fm.Mbox(g.mbox['path'], g.thread, preload = 100)

        if mbox.thread_show:
            self.list_thread(mbox, node)
        else:
            self.list_plain(mbox, node)


def get_node(i = None):
    node = g.ui_list.getnode(i)
    if not node:
        return

    if not node.ctx:
        return

    return node, node.ctx


def MailDel():
    node, obj = get_node()

    # obj may be topic

    obj.delete()

    g.maillist.refresh()

def MailFold():
    node, mail = get_node()

    mail.mark_readed(True)
    mail.set_fold()

    g.maillist.refresh()

def MailFlag():
    node, mail = get_node()

    if mail.flag:
        mail.set_flag(0)
    else:
        mail.set_flag(1)
    g.maillist.refresh()


def set_read(i, thread = False):
    node, mail = get_node(i)
    mail.mark_readed(thread)
    return True

def MailMarkRead(cls):
    refresh = False
    if cls == 'sel':
        start, end = pyvim.selectpos()
        start = start[0]
        end = end[0]


        for i in range(start, end + 1):
            set_read(i)
            refresh = True

    if cls == 'one':
        l,c = vim.current.window.cursor
        refresh = set_read(l - 1)

    if cls == 'thread':
        l,c = vim.current.window.cursor
        refresh = set_read(l - 1, True)

    if refresh:
        g.maillist.refresh()

def switch_options(target):
    if target == 'thread':
        g.thread = not g.thread

    if target == 'exts':
        g.exts = not g.exts

    g.maillist.refresh()

def refresh():
    g.maillist.refresh()

@pyvim.cmd()
def MailNew():
    path = '~/.fm.d/draft/%s.mail' % time.time()
    path = os.path.expanduser(path)

    vim.command('e ' + path)
    vim.command("set filetype=fmreply")
    vim.command("set buftype=")

    b = vim.current.buffer

    b[0] = 'Date: ' + email.utils.formatdate(localtime=True)
    b.append('Message-Id: ' + fm.gen_msgid())
    b.append('From: %s <%s>' % (fm.conf.name, fm.conf.me))
    b.append('Subject: ')
    b.append('To: ')
    b.append('Cc: ')
    b.append('')
    b.append('')


def push_to_stash():
    node, obj = get_node()
    g.stash.append(obj.get_id())
    g.maillist.refresh()

def clear_stash():
    g.stash = []
    g.maillist.refresh()

def merge_topic():
    node, obj = get_node()

    obj.merge(g.stash)

    g.maillist.refresh()
    g.stash = []


menu = [
        ("Refresh",                     refresh),
        ("---------------------------", None),
        ("Fold Current thread",         MailFold),
        ("Mark Current Readed",         MailMarkRead, 'one'),
        ("Mark Thread Readed",          MailMarkRead, 'thread'),
        ("Set Flag",                    MailFlag),
        ("---------------------------", None),
        ("Sort By Thread or Plain",     switch_options, 'thread'),
        ("---------------------------", None),
        ("Create New Mail",             MailNew),
        ("---------------------------", None),
        ("More info",                   switch_options, "exts"),
        ("---------------------------", None),
        ("Delate Current Mail",         MailDel),
        ("---------------------------", None),
        ("Push to stash",               push_to_stash),
        ("Clear stash",                 clear_stash),
        ("Merge Topic",                 merge_topic),
        ]
