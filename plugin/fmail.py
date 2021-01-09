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



def menu(m):
    keys, handler = zip(*m)

    def finish(index):
        if index < 0:
            return

        h = handler[index]
        if not h:
            return

        item = m[index]
        if len(item) == 3:
            h(item[2])
        else:
            h()

    popup.PopupMenu(keys, finish)

@pyvim.cmd()
def MailMenu():
    menu(mlist.menu)


@pyvim.cmd()
def MailPageMenu():
    menu(mpage.menu)
