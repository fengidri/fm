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

    return ('> ' * level) + line


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
        b[0] ='Message-Id: ' + mail.Message_id()
        b.append('Date: '    + mail.Date())

        align_email_addr(b,
                'From:', mail.From(),
                'To:',   mail.To(),
                'Cc:',   mail.Cc())

        b.append('Subject: ' + mail.Subject())


    #b.append('')
    b.append('=' * 80)

    for line in mail.Body().split('\n'):
        line = line.replace('\r', '')
        line = mail_body_quote_handler(line)
        b.append(line)

    atta = mail.Attachs()
    if atta:
        b.append('')
        b.append('--')
        for a in atta:
            b.append("[-- %s --] %s" %(a[0], a[1]))
        b.append('')

    b.append('=' * 80)
    b.append('mbox:      %s' % mail.mbox)
    b.append('sub:       %s' % mail.sub_n)
    b.append('sub-real:  %s' % len(mail.get_reply()))
    b.append('size:      %s' % mail.size)
    b.append('')
    b.append('=%s' % mail.path)


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

    show(g.pager_mail)

def MailFilter():
    g.header_filter = not g.header_filter

    if g.pager_buf != vim.current.buffer:
        return

    show(g.pager_mail)


def MailAck():
    b = vim.current.buffer
    l = vim.current.window.cursor[0] - 1
    b[l] = 'Acked-by: %s <%s>' % (fm.conf.name, fm.conf.me)

def MailReview():
    b = vim.current.buffer
    l = vim.current.window.cursor[0] - 1
    b[l] = 'Reviewed-by: %s <%s>' % (fm.conf.name, fm.conf.me)

def mail_git_append():
    m = current_mail()
    subject = m.Subject()
    pos = subject.find(']')
    if pos > -1:
        subject = subject[pos:].strip()

    line = vim.current.line
    vgit.options.commit_log_append(line, target = subject)

menu = [
            ("Reply(R)   --- reply this mail",    reply),
            ("Header(H)  --- show raw headers",   MailHeader),
            ("Filter     --- show other headers", MailFilter),
            ("Send       --- send this mail",     MailSend),
            ("Ack        --- add Acked-By",       MailAck),
            ("Review     --- add Reviewed-By ",   MailReview),
            ("Git Append --- git commit log append",   mail_git_append),
            ]
