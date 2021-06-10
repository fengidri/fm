# -*- coding:utf-8 -*-
import json
import os

class MailBox(object):
    def __init__(self, email, alias = None):
        self.email = email
        self.alias = alias

        l = os.path.expanduser("~/.fm.d/")
        l = os.path.join(l, email)
        l = os.path.join(l, 'last_check')
        self.last_check = float(open(l).read())

class Conf:
    def __init__(self):
        path = '~/.fm.json'
        path = os.path.expanduser(path)
        j = open(path).read()
        c = json.loads(j)

        self.confd = os.path.expanduser("~/.fm.d")
        self.synclock = os.path.join(self.confd, 'sync.lock')

        self.user     = c['user']
        self.server   = c['server']['host']
        self.port     = c['server']['port']
        self.password = c['server']['password']
        self.folders =  c['server']['folders']
        self.procmail = os.path.join(self.confd, 'procmail.py')

        self.smtp_host = c['smtp']['host']
        self.smtp_port = c['smtp']['port']

        self.deliver = os.path.expanduser(c['deliver'])

        self.me = c.get('user')
        self.name = c.get('name', self.me.split('@')[0])

        self.mailbox = MailBox(c.get('user'))

        self.log_path = os.path.join(self.deliver, "mails.log")

conf = Conf()
