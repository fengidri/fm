# -*- coding:utf-8 -*-

from collections import defaultdict


thread        = True
default       = None
last_subject  = None
header_raw    = False
header_filter = True
pager_buf     = None
pager_mail    = None
mbox_name     = None
mbox          = None

topic_defopen = False

config_short_time    = False
config_relative_time = False

exts                = False # mail list exts
stash                = []
stash_info          = []
topic_opend         = []
topic_close         = []
tips = None
last_title = None
auto_markreaded = True
# show archived topic
archived = 0
fold_hide = True

# cache for reply file.
# key: mail path
# value: [reply path, send status]
path_reply = defaultdict(list)
head_mail_reply = defaultdict(list)
topic_reply = defaultdict(list)

# cache for path -> mail id, head mail id, topic id
cache_mail_topic = {}
