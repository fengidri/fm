#1 -*- coding:utf-8 -*-
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

f = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, f)

import fm


class g:
    default              = None
    last_subject         = None
    header_raw           = False
    pager_buf            = None
    pager_mail           = None
    mbox                 = None
    config_short_time    = True
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

    f = m.From().short
    if f != '':
        f = '%s' % f
    else:
        f = '==>'

    f = f.ljust(15)[0:15]

    fmt = '{stat} {subject} {_from} {date}'
    fmt = '  {stat} {_from} {date} {subject} [{mbox}]'
    return fmt.format(stat = stat,
                   subject = subject,
                   _from = f,
                   date = date, mbox = m.mbox);

def align_email_addr(buf, *c):
    lines = []

    for i in range(0, len(c), 2):
        field = c[i]
        h = c[i + 1]
        if not h:
            continue

        if not isinstance(h, list):
            h = [h]

        for a in h:
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


    #b.append('')
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
    b.append('FM:')
    b.append('short keys:')
    b.append('    R: reply  H: raw heder show  q: exit' )
    b.append('')
    b.append('command:')
    b.append('    MailSend:     send email' )
    b.append('    MailSavePath: save current mail path to file(env: mail_path)' )
    b.append('    MailDel:      delete email' )
    b.append('')
    b.append('more info:')
    b.append('  mbox:      %s' % mail.mbox)
    b.append('  sub:       %s' % mail.sub_n)
    b.append('  sub-real:  %s' % len(mail.get_reply()))
    b.append('  size:      %s' % mail.size)
    b.append('')
    b.append('=%s' % mail.path)


def mail_show(mail):
    vim.command("set filetype=fmpager")
    vim.command("setlocal modifiable")

    _mail_show(mail)

    vim.command("setlocal nomodifiable")

def fm_mail_handle(leaf, listwin):
    mail = leaf.ctx

    if mail.isnew:
        mail.mark_readed()

        leaf.update(index_line(mail))

    mail_show(mail)

    g.pager_buf = vim.current.buffer
    g.pager_mail = mail


def fm_mail_list(node, listwin):
    ms = g.mbox.output(reverse=True)

    head = None
    node.append(frainui.Leaf('', None, None))

    for m in ms:
        first = False
        if head:
            if head != m.thread_head:
                first = True
                # empty line
                node.append(frainui.Leaf('-' * 130, None, None))

                head = m.thread_head
        else:
            head = m.thread_head
            first = True

        if first:
            c = m.Subject()
            c = 'T: ' + c
            node.append(frainui.Leaf(c, None, None))


        need_hide_subject(m)

        s = index_line(m)

        name = os.path.basename(m.path)

        l = frainui.Leaf(name, m, fm_mail_handle, display = s, last_win=True)
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


def reply_copy_header(mail, header):
    v = mail.header(header)
    if v:
        vim.current.buffer.append("%s: %s" % (header, v))

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

    b = vim.current.buffer

    b[0] = 'Message-Id: ' + fm.gen_msgid()
    b.append('Subject: ' + Subject)
    b.append('Date: ' + email.utils.formatdate(localtime=True))
    b.append('From: %s <%s>' % (fm.conf.name, fm.conf.me))


    if m.From():
        b.append('To: ' + m.From().format())

    if m.Cc():
        c = m.Cc()
        to = m.To()
        for a in c:
            if a.addr == fm.conf.me:
                c.remove(a)

        for a in to:
            if a.addr != fm.conf.me:
                c.append(a)

        b.append('Cc: ' + c.format())

    if m.Message_id():
        b.append('In-Reply-To: ' + m.Message_id())

    # for list-id
    reply_copy_header(m, "List-ID")
    reply_copy_header(m, "X-Mailing-List")

    b.append('')

    b = b

    b.append('On %s, %s wrote:' % (m.Date(), m.From().format()))

    lines = m.Body().split('\n')
    for line in lines:
        b.append('> ' + line.replace('\r', ''))

@pyvim.cmd()
def MailNew():
    path = '~/.fm.d/draft/%s.mail' % time.time()
    path = os.path.expanduser(path)

    vim.command('vs ' + path)
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
    vim.command("update")

    path = vim.current.buffer.name

    ret = fm.sendmail(path)

    if ret:
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

    pyvim.echo('save mail path to %s' % f)


@pyvim.cmd()
def MailHeader():
    g.header_raw = not g.header_raw

    if g.pager_buf != vim.current.buffer:
        return

    mail_show(g.pager_mail)



