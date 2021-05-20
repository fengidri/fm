import time
import frainui
from frainui import LIST
import fm
import g
import vim
import popup

def fm_mbox_handle(node, listwin):
    g.mbox_name = node.ctx

    g.maillist.refresh()
    vim.current.window.cursor = (1, 0)

def fm_mbox_list(node, listwin):
    width = 19
    show = (' ' * width) + 'Unread'
    node.append(frainui.Leaf(show, None, None))

    unread = fm.unread_stats()

    for b in fm.boxes():
        u = unread.get(b, 0)
        if u:
            show = '%s%s' % (b.ljust(width), u)
        else:
            show = b

        r = frainui.Leaf(show, b, fm_mbox_handle)
        node.append(r)

        if not g.default:
            g.default = r

def init():
    ui_mbox = LIST("FM Mbox", fm_mbox_list, title = fm.conf.me)
    ui_mbox.show()
    ui_mbox.refresh()

    def unread_change():
        ui_mbox.refresh()

    fm.unread_ev_bind(unread_change)

    if time.time() - fm.last_check_ts() > 60 * 5:
        check = time.localtime(fm.conf.mailbox.last_check)
        check = time.strftime("%y/%m/%d %H:%M", check)
        popup.PopupDialog('\n\n\t\tNotify: Last Check Is ' + check)

    g.ui_mbox = ui_mbox
