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
    fm.setup()
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
        menu = []
        for m in mlist.menu:
            menu.append(m[1:])

        popup.PopupMenu(menu, hotkey = False, title = 'Fmail List Menu')
    else:
        for m in mlist.menu:
            if m[0] == sel:
                if len(m) == 4:
                    m[2](m[3])
                else:
                    m[2]()

@pyvim.cmd()
def MailPageMenu(sel = None):
    if not sel:
        popup.PopupMenu(mpage.page_menu, hotkey = False, title = 'Fmail Page Menu')
    elif sel == 'reply':
        mpage.reply()
    elif sel == 'header':
        mpage.switch_options('header')
        mpage.switch_options('filter')




@pyvim.cmd()
def MailReplyMenu(sel = None):
    if not sel:
        popup.PopupMenu(mpage.reply_menu, hotkey = False, title = 'Fmail Reply Menu')









