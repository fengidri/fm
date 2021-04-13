
map <buffer> q :q<cr>
map <buffer> <C-n> <C-w>hj<cr>
map <buffer> <C-p> <C-w>hk<cr>

setlocal buftype=nofile
setlocal noswapfile
setlocal winwidth=90

map <buffer> <F2> :MailPageMenu<cr>
map <buffer> m :MailPageMenu<cr>
map <buffer> R :MailPageMenu reply<cr>
map <buffer> H :MailPageMenu header<cr>

set preserveindent
set cinoptions=(0,:0
set cindent
set colorcolumn=81
set tabstop=8
set softtabstop=8
set shiftwidth=8
set noexpandtab
