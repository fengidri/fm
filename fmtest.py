# -*- coding:utf-8 -*-


if __name__ == "__main__":
    pass

import fm
import sys
mbox = fm.Mbox(sys.argv[1], preload = 100)

topics = mbox.get_topics()



