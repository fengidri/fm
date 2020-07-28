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

class g:
    default = None
    last_subject = None
    listwin = None
    header_raw = False
    pager_buf = None
    pager_mail = None

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

def show_header_align(buf, *c):
    fields = []
    addrs = []

    i = -1;
    while True:
        i = i + 1
        if i >= len(c) / 2:
            break
        if not c[i * 2 + 1]:
            continue

        fields.append(c[i * 2])
        addrs.append(c[i * 2 + 1])

    name_len = 0
    alias_len = 0

    for ii, h in enumerate(addrs):
        h = h.replace('\n', '').replace('\r', '').split(',')
        for i, a in enumerate(h):
            a = fm.EmailAddr(a)
            h[i] = a

            if a.alias and len(a.alias) > alias_len:
                alias_len = len(a.alias)

            if len(a.name) > name_len:
                name_len = len(a.name)

        addrs[ii] = h

    field_len = max([len(x) for x in fields])

    for i, f in enumerate(fields):
        h = addrs[i]

        a = h[0]

        if a.name:
            _n = name_len - len(a.name)
        else:
            _n = name_len

        alias = a.alias
        if not alias:
            alias = ''

        line = '%s %s %s%s' % (f.ljust(field_len),
                alias.ljust(alias_len),
                ' ' * _n,
                a.addr)

        buf.append(line)
        for a in h[1:]:
            alias = a.alias
            if not alias:
                alias = ''

            if a.name:
                _n = name_len - len(a.name)
            else:
                _n = name_len

            line = '%s %s %s%s' % (' ' * field_len,
                    alias.ljust(alias_len),
                    ' ' * _n,
                    a.addr)
            buf.append(line)

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

        show_header_align(b,
                'From:', mail.From(),
                'To:',   mail.To(),
                'Cc:',   mail.Cc())


    b.append('')
    b.append('=' * 80)

    for line in mail.Body().split('\n'):
        b.append(line.replace('\r', ''))

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

    vim.command("setlocal nomodifiable")



def mail_show(leaf, listwin):
    mail = leaf.ctx

    if mail.isnew:
        mail.mark_readed()

        leaf.update(index_line(mail))

    _mail_show(mail)

    g.pager_buf = vim.current.buffer
    g.pager_mail = mail


def pager_refresh():
    if g.pager_buf != vim.current.buffer:
        return

    _mail_show(g.pager_mail)






def show_index(node, listwin):
    mdir = node.ctx
    mbox = fm.Mbox(mdir['path'])

    ms = mbox.output(reverse=True)

    head = None
    for m in ms:
        if head != m.thread_head:
            if (head and head.num() > 1) or m.thread_head.num() > 1:
                l = frainui.Leaf('', None, None)
                node.append(l)

            head = m.thread_head

        need_hide_subject(m)

        s = index_line(m)

        name = os.path.basename(m.path)

        l = frainui.Leaf(name, m, mail_show, display = s)
        node.append(l)


def list_root(node, listwin):

    for mdir in fm.conf.mbox:

        r = frainui.Node(mdir['name'], mdir, show_index)
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

    listwin = LIST("frain", list_root, ft='fmindex',
            use_current_buffer = True)

    listwin.show()
    listwin.refresh()
    if g.default:
        g.default.node_open()

    g.listwin = listwin

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
    node = g.listwin.getnode()
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
def MailSaveId():
    line = vim.current.buffer[-1]
    if line[0] != '=':
        return

    path = line[1:]

    m = fm.Mail(path)
    subject = m.Subject()
    Id = m.Message_id()

    f = os.environ.get('message_id_file')
    if not f:
        return

    open(f, 'w').write('%s\n%s\n' % (subject, Id))

    pyvim.echo('save message-id to %s' % f)


@pyvim.cmd()
def MailHeader():
    g.header_raw = not g.header_raw
    pager_refresh()
