# -*- coding:utf-8 -*-


if __name__ == "__main__":
    pass

import fm
import sys
mbox = fm.Mbox(sys.argv[1])
topic = mbox.topics[0]
print(len(topic.tops))
print(len(topic.mails))
for m in topic.output(True):
    l = '  ' * m.index + m.Subject() + m.In_reply_to()
    print(l)


