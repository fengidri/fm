# -*- coding:utf-8 -*-
import pyvim
import fm
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

class g:
    default = None
    last_subject = None
    header_raw = False
    pager_buf = None
    pager_mail = None
    mbox = None
    config_short_time = True
    config_relative_time = True

def need_hide_subject(m):
    m.hide_subject = False

    subject = m.Subject()
    if m.index > 0:
        if subject.startswith('Re: '):
            if subject[4:] == g.last_subject:
                m.hide_subject = True
                return
        else:
            if subject == g.last_subject:
                m.hide_subject = True
                return

    g.last_subject = subject


def index_line(m):
    if m.isnew:
        stat = '*'
    else:
        stat = ' '

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
                date = '%dday %s' % (day, hm)
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


    if m.hide_subject:
        subject = ''
    else:
        subject = m.Subject()

    subject = '%s %s' % (m.thread_prefix(), subject)
    subject = subject.ljust(90)[0:90]

    f = m.From()
    f = fm.EmailAddr(f)
    f = f.short
    if f != '':
        f = '%s' % f
    else:
        f = 'me'

    f = f.ljust(20)[0:20]

    fmt = '{stat} {subject} {_from} {date}'
    return fmt.format(stat = stat,
                   subject = subject,
                   _from = f,
                   date = date);



def show_header_addr(b, n, h):
    if not h:
        return

    t = h.replace('\n', '').split(',')

    b.append(n + t[0])
    for tt in t[1:]:
        b.append('   ' + tt)

def align_email_addr(buf, *c):
    lines = []

    for i in range(0, len(c), 2):
        field = c[i]
        header = c[i + 1]

        h = header.replace('\n', '').replace('\r', '').split(',')

        for a in h:
            a = fm.EmailAddr(a)

            show = a.alias
            if not show:
                show = a.name

            lines.append((field, show, a.server))
            field = ''

    lens = [0, 0, 0]

    for line in lines:
        for i, l in enumerate(lens):
            t = len(line[i])
            if l < t:
                lens[i] = t

    fmt = '%%-%ds %%-%ds @%%-%ds' % tuple(lens)

    for line in lines:
        line = fmt % line
        buf.append(line)


def mail_body_quote_handler(line):
    level = 0
    while True:
        if not line:
            break

        if line[0] != '>':
            break

        level += 1
        line = line[1:]

        if not line:
            break

        if line[0] == ' ':
            line = line[1:]

    return ('> ' * level) + line

def _mail_show(mail):
    vim.command("set filetype=fmpager")
    vim.command("setlocal modifiable")

    b = vim.current.buffer
    del b[:]

    if g.header_raw:
        for k,v in mail.get_mail().items():
            v = v.replace('\r', '')
            v = v.split('\n')

            s = '%s: %s' %(k, v[0])
            b.append(s)
            for t in v[1:]:
                b.append(t)

    else:
        s = 'Subject: ' + mail.Subject()

        b[0] = s

        b.append('Date: ' + mail.Date())

        align_email_addr(b,
                'From:', mail.From(),
                'To:',   mail.To(),
                'Cc:',   mail.Cc())


    b.append('')
    b.append('=' * 80)

    for line in mail.Body().split('\n'):
        line = line.replace('\r', '')
        line = mail_body_quote_handler(line)
        b.append(line)

    atta = mail.Attachs()
    if atta:
        b.append('')
        b.append('--')
        for a in atta:
            b.append("[-- %s --] %s" %(a[0], a[1]))
        b.append('')

    b.append('=' * 80)
    b.append('fm info:')
    b.append('=%s' % mail.path)
    b.append('R: reply  H: raw heder show  q: exit' )

    vim.command("setlocal nomodifiable")


def fm_mail_handle(leaf, listwin):
    mail = leaf.ctx

    if mail.isnew:
        mail.mark_readed()

        leaf.update(index_line(mail))

    _mail_show(mail)

    g.pager_buf = vim.current.buffer
    g.pager_mail = mail




def fm_mail_list(node, listwin):
    ms = g.mbox.output(reverse=True)

    head = None
    node.append(frainui.Leaf('', None, None))

    for m in ms:
        if head:
            if head != m.thread_head:
                if head.num() > 1 or m.thread_head.num() > 1:
                    node.append(frainui.Leaf('', None, None))

                head = m.thread_head
        else:
            head = m.thread_head

        need_hide_subject(m)

        s = index_line(m)

        name = os.path.basename(m.path)

        l = frainui.Leaf(name, m, fm_mail_handle, display = s, new_win=True)
        node.append(l)



def fm_mbox_handle(node, listwin):
    mdir = node.ctx
    mbox = fm.Mbox(mdir['path'])

    g.mbox = mbox

    g.ui_list.title = "MBox: %s thread: %s" % (mdir['name'], len(mbox.top))

    g.ui_list.show()
    g.ui_list.refresh()




def fm_mbox_list(node, listwin):
    check = time.localtime(fm.conf.mailbox.last_check)
    check = time.strftime("%y/%m/%d %H:%M", check)
    node.append(frainui.Leaf('check: %s' % check, None, None))
    node.append(frainui.Leaf('', None, None))

    for mdir in fm.conf.mbox:

        r = frainui.Leaf(mdir['name'], mdir, fm_mbox_handle)
        node.append(r)

        if mdir.get('default'):
            g.default = r


@pyvim.cmd()
def Mail():
    fm.init()

    b = vim.current.buffer
    if len(b) != 1:
        return

    if not fm.conf.mbox:
        return

    ui_mbox = LIST("FM Mbox", fm_mbox_list, title = fm.conf.me)

    ui_list = LIST("FM List", fm_mail_list, ft='fmindex',
            use_current_buffer = True, title = 'FM List')

    ui_mbox.show()
    ui_mbox.refresh()

    g.ui_list = ui_list
    g.ui_mbox = ui_mbox

    if g.default:
        g.default.node_open()

@pyvim.cmd()
def MailReply():
    line = vim.current.buffer[-1]
    if line[0] != '=':
        return

    path = line[1:]
    m = fm.Mail(path)

    path = '~/.fm.d/draft/%s.mail' % time.time()
    path = os.path.expanduser(path)

    vim.command('e ' + path)
    vim.command("set filetype=fmreply")
    vim.command("set buftype=")

    Subject = m.Subject()
    if not Subject.startswith('Re:'):
        Subject = 'Re: ' + Subject

    vim.current.buffer[0] = 'Subject: ' + Subject
    vim.current.buffer.append('Date: ' + email.utils.formatdate(localtime=True))

    vim.current.buffer.append('From: %s <%s>' % (fm.conf.name, fm.conf.me))

    if m.From():
        vim.current.buffer.append('To: ' + m.From().replace('\n', ' '))
    if m.Cc():
        c = m.Cc().split(',')
        c = [x.strip() for x in c]

        to = m.To().split(',')
        for t in to:
            t = t.strip()
            a = fm.EmailAddr(t)
            if a.addr != fm.conf.me:
                c.append(t)

        c = ', '.join(c)
        vim.current.buffer.append('Cc: ' + c)

    if m.Message_id():
        vim.current.buffer.append('In-Reply-To: ' + m.Message_id())

    vim.current.buffer.append('')

    b = vim.current.buffer

    b.append('On %s, %s wrote:' % (m.Date(), m.From()))

    lines = m.Body().split('\n')
    for line in lines:
        vim.current.buffer.append('> ' + line.replace('\r', ''))


@pyvim.cmd()
def MailDel():
    node = g.ui_list.getnode()
    if not node:
        return

    if not node.ctx:
        return

    if not isinstance(node, frainui.Leaf):
        return

    mail = node.ctx
    mail.delete()
    node.update(' ')

@pyvim.cmd()
def MailSend():
    path = vim.current.buffer.name

    code, out, err = fm.sendmail(path)

    if 0 == code:
        vim.command('set buftype=nofile')
        pyvim.echo('send success')
        return

    pyvim.echo('send fail')


@pyvim.cmd()
def MailSavePath():
    node = g.ui_list.getnode()
    if not node:
        return

    if not node.ctx:
        return

    mail = node.ctx
    path = mail.path

    #line = vim.current.buffer[-1]
    #if line[0] != '=':
    #    return


    #path = line[1:]

    #vim.command('silent !echo %s' % path)
    #vim.command('redraw!')

    f = os.environ.get('mail_path')
    if not f:
        return

    open(f, 'w').write(path)

    pyvim.echo('save mail path to console')


@pyvim.cmd()
def MailHeader():
    g.header_raw = not g.header_raw

    if g.pager_buf != vim.current.buffer:
        return

    _mail_show(g.pager_mail)



