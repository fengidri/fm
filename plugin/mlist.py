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



def check_reply(d, key):
    v = d.get(key)
    if not v:
        return False

    for r in v:
        if not r[1]: # reply not send
            return True

    return False


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

    def str_subject(self, m):
        head = m.thread_head

        if head == m:
            return m.Subject().strip()

        head_features = head.features()
        mail_features = m.features()

        fs = []

        for f in mail_features:
            if f in head_features:
                continue

            fs.append(f)

        return '%s. %s' % (' '.join(fs),  m.subject_nofeature())


    def strline(self, m):
        stat = '   '
        if m.isnew:
            if m.From().isme:
                m.mark_readed()
            else:
                stat = '*  '

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
        else:
            subject = self.str_subject(m)


        ext = ''
        if g.exts:
            if m == m.thread_head:
                ext += ' (%d)' % m.num()

        if short_msg:
            short_msg = token(short_msg, 'shortmsg')

        if g.thread:
            fmt = '{stat}  {date} {prefix}{from_name} {subject}{short_msg}'
        else:
            fmt = ' {stat} {date} {subject} {topic}'

        return fmt.format(
                stat      = stat,
                date      = date,
                prefix    = prefix,
                from_name = from_name,
                subject   = subject,
                short_msg = short_msg
                )

    def reply_edit(self, leaf, listwin):
        mail = leaf.ctx

        mpage.reply_edit(mail)

        g.pager_buf = vim.current.buffer
        g.pager_mail = mail


    def mail_show(self, leaf, listwin):
        mail = leaf.ctx

        if g.auto_markreaded and mail.isnew:
            mail.mark_readed()

            leaf.update(self.strline(mail))

            father = leaf.father
            topic = father.ctx

            prefix, line = self.topic_line(topic)
            father.update(line, prefix)

        mpage.show(mail)

        # for short_msg
        leaf.update(self.strline(mail))

        g.pager_buf = vim.current.buffer
        g.pager_mail = mail

    def check_reply(self, node, mail):
        reply = g.path_reply.get(mail.path)
        if not reply:
            return

        for r in reply:
            if r[1]:
                continue

            m = fm.Mail(r[0])

            name = (" " * 30)  + "Reply-UNDONE"

            l = frainui.Leaf(name, m, self.reply_edit,
                    display = name, last_win=True, noindent = True)

            node.append(l)

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

            has_reply = check_reply(g.head_mail_reply, head.rowid)

            if g.fold_hide and head.fold and head.news() == 0 and not has_reply:
                hide_mail = True
                continue

            need_hide_subject(m)

            m.hide_title = False
            s = self.strline(m)
            g.last_title = m.title()

            name = os.path.basename(m.path)

            l = frainui.Leaf(name, m, self.mail_show, display = s,
                    last_win=True, noindent = True)

            node.append(l)
            last = l

            self.check_reply(node, m)

        if last:
            node.append(frainui.Leaf('', None, None))

        if hide_mail:
            node.append(frainui.Leaf('   === SOME MAIL HIDDEN ===', None, None))
            node.append(frainui.Leaf('   ', None, None))

        g.last_title = None

    def topic_defopen(self, topic):
        defopen = False

        if topic.get_ignore():
            return False

        if g.topic_defopen:
            if topic.loaded():
                defopen = True
            else:
                if topic.get_id() in g.topic_opend:
                    defopen = True
        else:
            if topic.get_unread():
                return True

            defopen = check_reply(g.topic_reply, topic.get_rowid())
            if defopen:
                return True

            if time.time() - topic.timestamp() < 3600 * 24:
                defopen = True

        return defopen

    def topic_line(self, topic):
        if topic.get_id() in g.stash:
            unread = '@  '
        else:
            if topic.get_ignore():
                    unread = 'I  '
                    unread = token(unread, 'unread')
            else:
                if topic.get_unread() > 0:
                    unread = '%-2d ' % topic.get_unread()
                    unread = token(unread, 'unread')
                else:
                    unread = '   '

        prefix = unread
        line = topic.topic()

        if g.exts:
            e = ' id: %d' % topic.get_id()
            line += e

        return prefix, ' ' + line

    def list_topic(self, mbox, node, start):
        topics = mbox.get_topics()

        node.append(frainui.Leaf('', None, None))

        for topic in topics:
            defopen = self.topic_defopen(topic)
            prefix, line = self.topic_line(topic)

            n = frainui.Node(line, topic, self.topic_list,
                    isdir = False,
                    defopen = defopen,
                    prefix = prefix)

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
            self.list_topic(mbox, node, start)
        else:
            self.list_plain(mbox, node, start)


def get_node(i = None):
    node = g.ui_list.getnode(i)
    if not node:
        return

    if not node.ctx:
        return

    return node, node.ctx


def MailDel(_):
    node, obj = get_node()

    # obj may be topic

    obj.delete()

    g.maillist.refresh()

def MailFold(_):
    node, mail = get_node()

    mail.mark_readed(True)
    mail.set_fold()

    g.maillist.refresh()

def TopicArchived(_):
    node, topic = get_node()

    topic.set_archived()

    g.maillist.refresh()

def MailFoldOther(_):
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

def MailFlag(_):
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

def MailMarkIgnore(_):
    node, obj = get_node()
    obj.set_ignore()
    g.maillist.refresh()
    g.ui_mbox.refresh()

def switch_options(target):
    if target == 'thread':
        g.thread = not g.thread

    if target == 'exts':
        g.exts = not g.exts

    if target == 'archived':
        g.archived = not g.archived

    if target == 'fold':
        g.fold_hide = not g.fold_hide

    if target == 'defopen':
        g.topic_defopen = not g.topic_defopen


    g.maillist.refresh()

def refresh(_):
    g.maillist.refresh()

def download(_):
    popup.PopupRun(fm.syncmail.sync, title = 'fm mail sync',
            maxwidth=160,
            wrap = False)

    g.maillist.refresh()

@pyvim.cmd()
def MailNew(_ = None):
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


def push_to_stash(_):
    node, obj = get_node()
    g.stash.append(obj.get_id())
    g.maillist.refresh()
    if g.tips:
        g.tips.close()

    g.stash_info.append(obj.topic())

    g.tips = popup.PopupTips(g.stash_info)

def clear_stash(_):
    g.stash = []
    g.stash_info = []
    g.tips.close()

    g.maillist.refresh()

def merge_topic(_):
    node, obj = get_node()

    obj.merge(g.stash)

    g.maillist.refresh()

    g.stash = []
    g.stash_info = []
    g.tips.close()

def move_to_mbox(_):
    node, obj = get_node()

    sel = fm.boxes()

    def f(i):
        if i < 0:
            return

        mbox = sel[i]
        obj.set_mbox(mbox)
        g.maillist.refresh()

    popup.PopupSelect(sel, f, title='Select Mbox. <esc> cancel', maxwidth=40)


menu = []


def m_append(show, call = None, arg = None, key = None):
    i = popup.PopupMenuItem(show, call, arg)
    i.key = key
    menu.append(i)

m_append("Refresh.               r", refresh, None, "Refresh")
m_append("Download.", download)

m_append("")
m_append("====== mark ===============")
m_append("Mark Mail Readed",         MailMarkRead,   'one')
m_append("Mark Mail Flag         f", MailFlag,       None, "Flag")
m_append("Mark Thread Readed",       MailMarkRead,   'thread')
m_append("Mark All Readed",          MailMarkRead,   'all')
m_append("Mark Ignore            I", MailMarkIgnore, None, "Ignore")

m_append("")
m_append("====== fold/archived ======")
m_append("Archived Topic         A", TopicArchived, None, "Archived")
m_append("Fold Thread            F", MailFold, None, "Fold")
m_append("Fold Other Thread",        MailFoldOther)
m_append("Move Mbox",                move_to_mbox)

m_append("")
m_append("====== show opt ===========")
m_append("Show Archived",   switch_options, 'archived')
m_append("Show Plain",      switch_options, 'thread')
m_append("Show Ext info",   switch_options, "exts")
m_append("Show Fold",       switch_options, "fold")
m_append("Show Topic Fold", switch_options, "defopen")

m_append("")
m_append("====== option =============")
m_append("Create Mail",                 MailNew)
m_append("Delete Mail/Topic",           MailDel)

m_append("")
m_append("====== topic merge ========")
m_append("Push topic to stash",         push_to_stash)
m_append("Clear stash",                 clear_stash)
m_append("Merge stash to current Topic",merge_topic)
