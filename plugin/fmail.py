# -*- coding:utf-8 -*-
import pyvim
import fm
import vim

from frainui import LIST
import frainui
from pyvim import log as logging
import time
import email
import os


class g:
    default = None
    last_subject = None
    listwin = None
    header_raw = True
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


def display(m):
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
        f = 'From: %s' % f

    f = f.ljust(20)[0:20]

    fmt = '{stat} {subject} \\green;{_from}\\end; {date}'
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



def _mail_show(mail):
    vim.command("set filetype=fmpager")
    vim.command("setlocal modifiable")

    b = vim.current.buffer
    del b[:]

    if g.header_raw:
        for k,v in mail.mail.items():
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
        b.append('From: ' + mail.From())

        show_header_addr(b, 'To: ', mail.To())
        show_header_addr(b, 'Cc: ', mail.Cc())

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

    b.append('--')
    b.append('=%s' % mail.path)

    vim.command("setlocal nomodifiable")

    if mail.isnew:
        mail.mark_readed()

        mail.isnew = False

        leaf.update(display(mail))

    b.append('--')
    b.append('=%s' % mail.path)

    vim.command("setlocal nomodifiable")



def mail_show(leaf, listwin):
    mail = leaf.ctx
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
            if head:
                l = frainui.Leaf('', None, None)
                node.append(l)

            head = m.thread_head

        need_hide_subject(m)

        s = display(m)

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
