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
import popup

import subprocess
import datetime
import sys

import fm
import g
import mpage

def token(t, tp):
    return '\\%s;%s\\end;' % (tp, t)

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
                ts = time.time() - date
                if ts < 3600 * 36:
                    date = '-%dH' % (ts / 3600)
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
        if m.isnew and not m.From().isme:
            stat = '  *'
        else:
            stat = '   '

        if m.flag:
            stat += '⚑'
        else:
            stat += ' '

        date = self.strdate(m)
        if time.time() - m.Date_ts() < 3600 * 24:
            date = token(date, 'time')

        f = m.From().short
        if not f:
            f = 'Me'

        f = token(f, 'name')

        if m.hide_title:
            subject = f
            f = None
        elif m.title() == g.last_title and m != m.thread_head and g.thread:
            subject = f
            f = None
            m.hide_title = True
        else:
            g.last_title = m.title()
            subject =  m.Subject().strip()
            subject = '%s: %s' %(f, subject)

        if m.parent:
            i1 = m.parent.index * '|   '
            prefix = '%s|---' %(i1, )
            subject = prefix + subject

        l = 120

        if m.fold:
            suffix = ' ......'
            l = l - len(suffix)
            if len(subject) > l:
                subject = subject[0: l]
            else:
                subject = subject.ljust(l)

            subject += suffix

        else:
            if len(subject) >= l:
                if f:
                    suffix = '...'
                    subject = subject[0:l - len(suffix)]
                    subject += suffix
            else:
                subject = subject.ljust(l)


        ext = ''
        if m == head:
            ext += ' (%d)' % m.num()

        if g.exts:
            fmt = '{stat} {subject} {date} {ext} {mbox} {rowid} {topic_id}'
        elif g.thread:
            if m.short_msg:
                fmt = '{stat} {date} {subject} | {short_msg}'
            else:
                fmt = '{stat} {date} {subject}'
        else:
            fmt = '{stat} {date} {subject} {topic}'

        return fmt.format(stat = stat,
                subject = subject,
                date = date,
                ext = ext,
                mbox = m.mbox,
                rowid = m.rowid,
                topic = '', # TODO
                short_msg = m.short_msg[0:60],
                topic_id=m.topic_id);

    def strline(self, m, head = None):
        if m.isnew and not m.From().isme:
            stat = '  *'
        else:
            stat = '   '

        if m.flag:
            stat += '⚑'
        else:
            stat += ' '

        date = self.strdate(m)
        if time.time() - m.Date_ts() < 3600 * 24:
            date = token(date, 'time')

        f = m.From().short
        if not f:
            f = 'Me'

        from_name = token(f, 'name')
        subject = m.Subject().strip()

        if m.parent:
            i1 = m.parent.index * '|   '
            prefix = '%s|---' %(i1, )
        else:
            prefix = ''

        short_msg = ''
        if m.hide_title:
            subject = ''
            short_msg = m.short_msg[0:60]
        elif m.title() == g.last_title and m != m.thread_head and g.thread:
            subject = ''
            short_msg = m.short_msg[0:60]
            m.hide_title = True


        ext = ''
        if g.exts:
            if m == head:
                ext += ' (%d)' % m.num()

        if short_msg:
            short_msg = token(short_msg, 'shortmsg')

        if g.thread:
            fmt = '{stat} {date} {prefix}{from_name}: {subject}{short_msg}'
        else:
            fmt = '{stat} {date} {subject} {topic}'

        return fmt.format(
                stat      = stat,
                date      = date,
                prefix    = prefix,
                from_name = from_name,
                subject   = subject,
                short_msg = short_msg
                )


    def mail_show(self, leaf, listwin):
        mail = leaf.ctx

        if g.auto_markreaded and mail.isnew:
            mail.mark_readed()

            leaf.update(self.strline(mail))

        mpage.show(mail)

        # for short_msg
        leaf.update(self.strline(mail))

        g.pager_buf = vim.current.buffer
        g.pager_mail = mail

    def topic_list(self, node, listwin):
        topic = node.ctx
        topic.load()

        g.topic_opend.append(topic.get_id())

        ms = topic.output(reverse=True)

        g.last_title = None

        head = None
        last = None
        hide_mail = False
        for m in ms:
            if head != m.thread_head:
                head = m.thread_head

                if last:
                    node.append(frainui.Leaf('', None, None))
                    last = None

            if g.fold_hide and head.fold and head.news() == 0:
                hide_mail = True
                continue

            need_hide_subject(m)

            m.hide_title = False
            s = self.strline(m, head)
            g.last_title = m.title()

            name = os.path.basename(m.path)

            l = frainui.Leaf(name, m, self.mail_show, display = s,
                    last_win=True, noindent = True)
            node.append(l)
            last = l

        if last:
            node.append(frainui.Leaf('', None, None))

        if hide_mail:
            node.append(frainui.Leaf('   === SOME MAIL HIDDEN ===', None, None))
            node.append(frainui.Leaf('   ', None, None))

        g.last_title = None

    def list_thread(self, mbox, node, start):
        topics = mbox.get_topics()

        node.append(frainui.Leaf('', None, None))

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

        self.ui_list.title = "MBox: %s. Time Spent: %.3fs Topic: %s. Archived: %s. Stash: %s." % (
                g.mbox_name, time.time() - start, len(topics), g.archived, len(g.stash))

    def list_plain(self, mbox, node, start):
        ms = mbox.output(reverse=True)
        self.ui_list.title = "MBox: %s num: %s" % (g.mbox_name, len(ms))

        head = None
        node.append(frainui.Leaf('', None, None))

        for m in ms:
            m.hide_title = False
            s = self.strline(m)

            name = os.path.basename(m.path)

            l = frainui.Leaf(name, m, self.mail_show, display = s, last_win=True)
            node.append(l)

    def list_handler(self, node, listwin):
        start = time.time()
        mbox = g.mbox = fm.Mbox(g.mbox_name, g.thread, preload = 100,
                archived = g.archived)

        if mbox.thread_show:
            self.list_thread(mbox, node, start)
        else:
            self.list_plain(mbox, node, start)


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

def TopicArchived():
    node, topic = get_node()

    topic.set_archived()

    g.maillist.refresh()

def MailFoldOther():
    node, mail = get_node()

    head = mail.thread_head
    topic = head.topic

    ts = head.topic.get_threads()

    for h in ts:
        if h == head:
            continue

        h.mark_readed(True)
        h.set_fold(True)

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

    if cls == 'all':
        g.mbox.mark_readed()
        refresh = True

    if refresh:
        g.maillist.refresh()

def switch_options(target):
    if target == 'thread':
        g.thread = not g.thread

    if target == 'exts':
        g.exts = not g.exts

    if target == 'archived':
        g.archived = not g.archived

    if target == 'fold':
        g.fold_hide = not g.fold_hide

    g.maillist.refresh()

def refresh():
    g.maillist.refresh()

def download():
    popup.PopupRun(fm.syncmail.sync, title = 'fm mail sync',
            maxwidth=160,
            wrap = False)

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
    if g.tips:
        g.tips.close()

    g.stash_info.append(obj.topic())

    g.tips = popup.PopupTips(g.stash_info)

def clear_stash():
    g.stash = []
    g.stash_info = []
    g.tips.close()

    g.maillist.refresh()

def merge_topic():
    node, obj = get_node()

    obj.merge(g.stash)

    g.maillist.refresh()

    g.stash = []
    g.stash_info = []
    g.tips.close()


menu = [
        ("Refresh.               r",    refresh),
        ("Download.",  download),

        ("",                            None),
        ("====== mark ===============", None),
        ("Mark Mail Readed",            MailMarkRead, 'one'),
        ("Mark Mail Flag         f",    MailFlag),
        ("Mark Thread Readed",          MailMarkRead, 'thread'),
        ("Mark All Readed",             MailMarkRead, 'all'),

        ("",                            None),
        ("====== fold/archived ======", None),
        ("Archived Topic         A",    TopicArchived),
        ("Fold Thread            F",    MailFold),
        ("Fold Other Thread",           MailFoldOther),

        ("",                            None),
        ("====== show opt ===========", None),
        ("Toggle Thread/Plain",         switch_options, 'thread'),
        ("Toggle archived",             switch_options, 'archived'),
        ("Toggle ext info",             switch_options, "exts"),
        ("Toggle fold",                 switch_options, "fold"),

        ("",                            None),
        ("====== option =============", None),
        ("Create Mail",                 MailNew),
        ("Delete Mail/Topic",           MailDel),

        ("",                            None),
        ("====== topic merge ========", None),
        ("Push topic to stash",         push_to_stash),
        ("Clear stash",                 clear_stash),
        ("Merge stash to current Topic",merge_topic),
        ]
