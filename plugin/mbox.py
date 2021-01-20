import time
import frainui
from frainui import LIST
import fm
import g
import popup

def fm_mbox_handle(node, listwin):
    mdir = node.ctx

    g.mbox = mdir

    g.maillist.refresh()

def fm_mbox_list(node, listwin):
    node.append(frainui.Leaf('', None, None))

    for mdir in fm.conf.mbox:

        r = frainui.Leaf(mdir['name'], mdir, fm_mbox_handle)
        node.append(r)

        if mdir.get('default'):
            g.default = r


def init():
    ui_mbox = LIST("FM Mbox", fm_mbox_list, title = fm.conf.me)
    ui_mbox.show()
    ui_mbox.refresh()

    if time.time() - fm.last_check_ts() > 60 * 5:
        check = time.localtime(fm.conf.mailbox.last_check)
        check = time.strftime("%y/%m/%d %H:%M", check)
        popup.PopupDialog('\n\n\t\tNotify: Last Check Is ' + check)

    g.ui_mbox = ui_mbox
