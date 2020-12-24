# -*- coding:utf-8 -*-


if __name__ == "__main__":
    pass

import fm
import sys
mbox = fm.Mbox(sys.argv[1])
for m in mbox.output():
        l = '  ' * m.index + m.Subject() + m.In_reply_to()
#        print(l)


