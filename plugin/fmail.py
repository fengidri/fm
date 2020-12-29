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
    menu(mlist.menu)


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
