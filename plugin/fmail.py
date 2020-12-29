import pyvim
import vim
import os
import sys
import popup
import frainui
import time
import email.utils

f = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, f)

import fm
import mbox
import mlist
import mpage
import g


@pyvim.cmd()
def Mail():
    b = vim.current.buffer
    if len(b) != 1:
        return

    if not fm.conf.mbox:
        return

    mbox.init()

    g.maillist = mlist.MailList()

    if g.default:
        g.default.node_open()

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

def MailFold():
    node = g.ui_list.getnode()
    if not node:
        return

    if not node.ctx:
        return

    if not isinstance(node, frainui.Leaf):
        return

    mail = node.ctx
    mail.set_fold()
    g.maillist.refresh()

@pyvim.cmd()
def MailMarkRead():
    start, end = pyvim.selectpos()
    start = start[0]
    end = end[0]

    refresh = False

    for i in range(start, end + 1):
        node = g.ui_list.getnode(i)
        if not node:
            continue

        if not node.ctx:
            continue

        if not isinstance(node, frainui.Leaf):
            continue

        mail = node.ctx
        mail.mark_readed()
        refresh = True

    if refresh:
        g.maillist.refresh()

def MailSend():
    vim.command("update")

    path = vim.current.buffer.name

    ret = fm.sendmail(path)

    if ret:
        vim.command('set buftype=nofile')
        pyvim.echo('send success')
        return

    pyvim.echo('send fail')

def MailHeader():
    g.header_raw = not g.header_raw

    if g.pager_buf != vim.current.buffer:
        return

    fmail.mail_show(g.pager_mail)

def MailFilter():
    g.header_filter = not g.header_filter

    if g.pager_buf != vim.current.buffer:
        return

    fmail.mail_show(g.pager_mail)

def MailThread():
    g.thread = not g.thread
    g.maillist.refresh()

def refresh():
    g.maillist.refresh()

def MailAck():
    b = vim.current.buffer
    l = vim.current.window.cursor[0] - 1
    b[l] = 'Acked-by: %s <%s>' % (fm.conf.name, fm.conf.me)

def MailReview():
    b = vim.current.buffer
    l = vim.current.window.cursor[0] - 1
    b[l] = 'Reviewed-by: %s <%s>' % (fm.conf.name, fm.conf.me)

def menu(m):
    keys, handler = zip(*m)

    def finish(index):
        if index < 0:
            return
        h = handler[index]
        if not h:
            return

        h()

    popup.PopupMenu(keys, finish)

@pyvim.cmd()
def MailMenu():
    menu([
            ("Refresh --- refresh",                       refresh),
            ("Fold    --- fold current thread",           MailFold),
            ("Thread  --- show by thread or plain",       MailThread),
            ("Delete  --- delate current mail",           MailDel),
            ("Readed  --- mark the selected mail readed", MailMarkRead),
            ("New     --- create new mail",               MailNew),
            ])


@pyvim.cmd()
def MailPageMenu():
    menu([
            ("Reply(R)  --- reply this mail",    mpage.reply),
            ("Header(H) --- show raw headers",   MailHeader),
            ("Filter    --- show other headers", MailFilter),
            ("Send      --- send this mail",     MailSend),
            ("Ack       --- add Acked-By",       MailAck),
            ("Review    --- add Reviewed-By ",   MailReview),
            ])
