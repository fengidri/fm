#1 -*- coding:utf-8 -*-
import vim
import pyvim
import g
import fm
import time
import os
import email
import email.utils
import vgit.options
import popup

def reply_copy_header(mail, header):
    v = mail.header(header)
    if v:
        vim.current.buffer.append("%s: %s" % (header, v))

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
    line = line.replace('\r', '')
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

    return level, ('> ' * level) + line

def mail_body(mail):
    lines = []
    reply_n = 0
    in_reply = False
    short_msg = []
    last_line = None
    head = True # before the first quote
    block_is_empty = False

    mail.first_reply_linenu = 0

    for i, line in enumerate(mail.Body().split('\n')):
        r, line = mail_body_quote_handler(line)
        lines.append(line)

        if head:
            if line.strip() == '':
                continue

            if r:
                head = False
                if last_line:
                    del short_msg[-1]

                if not short_msg:
                    mail.first_reply_linenu = 0
            else:
                last_line = line
                short_msg.append(line)
                if mail.first_reply_linenu == 0:
                    mail.first_reply_linenu = i

            continue

        if not r: # this line is reply
            if len(short_msg) < 5:
                short_msg.append(line.strip())

            if line.strip() != '':
                block_is_empty = False

                if mail.first_reply_linenu == 0:
                    mail.first_reply_linenu = i

        if r and in_reply: # go into quote
            if not block_is_empty:
                reply_n += 1
                lines.insert(-1, reply_n)

            in_reply = False

        if not r and not in_reply: # go into reply
            in_reply = True
            block_is_empty = True


    if in_reply and not block_is_empty:
        reply_n += 1
        lines.append(reply_n)

    o = []
    for line in lines:
        if type(line) == int:
            if line == reply_n:
                o.append('> === LAST REPLY ===')
        else:
            o.append(line)

    mail.short_msg = ' '.join(short_msg)

    return o


def header_filter(k):
    header_filter = ['Message-Id', 'Subject', 'Date',
            'From', 'To', 'Cc', 'In-Reply-To']

    if not g.header_filter:
        return True


    for h in header_filter:
        if h.lower() == k.lower():
            return True
    return False

def _mail_show(mail):
    b = vim.current.buffer
    del b[:]

    b[0] =  '=' * 80

    if g.header_raw:
        for k,v in mail.get_mail().items():
            if not header_filter(k):
                continue

            v = v.replace('\r', '')
            v = v.split('\n')

            s = '%s: %s' %(k, v[0])
            b.append(s)
            for t in v[1:]:
                b.append(t)

    else:
        b.append('Message-Id: ' + mail.Message_id())
        b.append('Date: '    + mail.Date())

        align_email_addr(b,
                'From:', mail.From(real = True),
                'To:',   mail.To(real = True),
                'Cc:',   mail.Cc(real = True))

        b.append('')

        s = mail.Subject()
        s = s.split(':', 1)
        b.append(s[0])
        if len(s) == 2:
            b.append('   ' + s[1])



        b.append('')


    b.append('=' * 80)

    header_num = len(b)

    b.append(mail_body(mail))

    atta = mail.Attachs()
    if atta:
        b.append('')
        b.append('--')
        for a in atta:
            b.append("[-- %s --] %s" %(a[0], a[1]))
        b.append('')

    b.append('=' * 80)
    b.append('size:      %s' % mail.size)
    b.append('')
    b.append('=%s' % mail.path)

    vim.current.window.cursor = (mail.first_reply_linenu + header_num + 1, 0)
    vim.command("normal zz")


def show(mail):
    vim.command("set filetype=fmpager")
    vim.command("setlocal modifiable")

    _mail_show(mail)

    vim.command("setlocal nomodifiable")

def current_mail():
    line = vim.current.buffer[-1]
    if line[0] != '=':
        return

    path = line[1:]
    return fm.Mail(path)

def reply():
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


def mail_send_handler(popup, path):
    popup.append("mail path: %s" % path)
    ret = fm.sendmail(popup, path)

    if ret:
        popup.append('send success')
        vim.command('set buftype=nofile')
        return

    popup.append('send fail')

def MailSend():
    vim.command("update")

    path = vim.current.buffer.name

    popup.PopupRun(mail_send_handler, path, title= 'FM Send Mail')

def switch_options(target):
    if target == 'header':
        g.header_raw = not g.header_raw
    elif target == 'filter':
        g.header_filter = not g.header_filter
    else:
        return

    if g.pager_buf != vim.current.buffer:
        return

    show(g.pager_mail)

def reply_by(h):
    b = vim.current.buffer
    l = vim.current.window.cursor[0] - 1
    b[l] = '%s: %s <%s>' % (h, fm.conf.name, fm.conf.me)

def mail_git_append():
    m = current_mail()
    subject = m.Subject()
    pos = subject.find(']')
    if pos > -1:
        subject = subject[pos:].strip()

    line = vim.current.line
    vgit.options.commit_log_append(line, target = subject)

def link_mail():

    line = vim.current.buffer[-1]
    if line[0] != '=':
        return

    path = line[1:]

    link = '/tmp/mail.link'
    if os.path.islink(link):
        os.remove(link)

    os.symlink(path, link)

    popup.PopupRun("cat %s|grep '^Subject:'" % link)

page_menu = [
            ("Reply ...",                   reply),
            ("===========================", None),
            ("Show raw headers",            switch_options, 'header'),
            ("Show other headers",          switch_options, 'filter'),
            ("===========================", None),
            ("Link mail to /tmp/mail.link", link_mail),
            ]

reply_menu = [
            ("Set Acked-By",                reply_by, 'Acked-by'),
            ("Set Reviewed-By ",            reply_by, 'Reviewed-by'),
            ("===========================", None),
            ("GIT Commit log append",       mail_git_append),
            ("===========================", None),
            ("Send ...",                    MailSend),
            ]
