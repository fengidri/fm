# -*- coding:utf-8 -*-

import subprocess
from email.mime.text import MIMEText
from email.header import Header
import smtplib
from . import mail
from . import conf
import os
import email
conf = conf.conf


def file_to_message(path):
    headers = {}

    from_ = None
    to = None

    lines = open(path).readlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            body = ''.join(lines[i + 1:])
            break

        field, header = line.split(':', 1)
        if not field or not header:
            continue

        field  = field.strip()
        header = header.strip()

        if field.lower() in ['to', 'cc']:
            h = mail.EmailAddrLine(header)
            header = h.to_str()
            if to == None:
                to = h
            else:
                to.extend(h)

        if field.lower() == 'from':
            h = mail.EmailAddrLine(header)
            header = h.to_str()
            from_ = h[0]

        headers[field] = header

    if body.isascii():
        message = MIMEText(body, 'plain', 'ascii')
    else:
        cs = email.charset.Charset('utf-8')
        cs.body_encoding = email.charset.QP
        message = MIMEText(body, 'plain', _charset=cs)

    for key, value in headers.items():
        message[key] = value

    return message, from_.simple(), to.simple_list()


def sendmail_imap(path):
    msg, from_, to = file_to_message(path)

    smtp = smtplib.SMTP_SSL(conf.smtp_host, conf.smtp_port)
    smtp.login(conf.user, conf.password)
    smtp.sendmail(from_, to, msg.as_string())



def sendmail_msmtp(path):
    msg, from_, to = file_to_message(path)

#    c = bytes(cstr, encoding='utf8')
    c = msg.as_bytes()

    cmd = ['msmtp', '-i']
    cmd.extend(to)

    p = subprocess.Popen(cmd,
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)

    stdout, stderr = p.communicate(c)

    code = p.returncode
    return code



def sendmail(path, imap = False):
    if imap:
        sendmail_imap(path)
    else:
        code = sendmail_msmtp(path)
        if code:
            return

    cstr = open(path).read()

    name = os.path.basename(path)
    sent = os.path.expanduser(os.path.join('~/.fm.d/sent', name))
    open(sent, 'w').write(cstr)

    os.remove(path)
    return True
