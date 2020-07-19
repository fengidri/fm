let s:script_folder_path = escape(expand('<sfile>:p:h' ), '\')

py3 <<EOF
import sys
import vim

sys.path.insert(0, vim.eval('s:script_folder_path'))

import fmail
EOF
