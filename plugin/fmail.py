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

    mbox.init()

    g.maillist = mlist.MailList()

    if g.default:
        g.default.node_open()

@pyvim.cmd()
def MailMenu(sel = None):
    if not sel:
        popup.PopupMenu(mlist.menu)
    elif sel == 'sort':
        mlist.switch_options('thread')
    elif sel == 'flag':
        mlist.MailFlag()
    elif sel == 'refresh':
        mlist.refresh()


@pyvim.cmd()
def MailPageMenu(sel = None):
    if not sel:
        popup.PopupMenu(mpage.menu)
    elif sel == 'reply':
        mpage.reply()
    elif sel == 'header':
        mpage.switch_options('header')
        mpage.switch_options('filter')













