""runtime syntax/mail.vim

""unlet b:current_syntax

""runtime syntax/diff.vim


syn match Identifier  'Reviewed-by'
syn match Identifier  'Acked-by'
syn match Identifier  'Signed-off-by'
syn match Identifier  'Co-Developed-by'
syn match ErrorMsg  'Fixes'
syn match Type  'Link'
syn match Type  'Reported-by'

syn match MailLine1   '^>'
syn match MailLine2   '^> >'lc=2
syn match MailLine3   '^> > >'lc=4
syn match MailLine4   '^> > > >'lc=6


hi MailLine1  guifg=#595959 guibg=#595959
hi MailLine2  guifg=#cccccc guibg=#cccccc
hi MailLine3  guifg=#1e7079 guibg=#1e7079
hi MailLine4  guifg=red     guibg=red


""syn region PreProc start='\c^[A-Za-z-]*:' end='^[^ \t]'me=e-1,he=e-1,re=s-1

syn match Title  '\c^subject: .*$'
syn match Index '\c^Date: .*$'
syn region Special start='\c^Cc:' end='^[^ \t]'me=e-1,he=e-1,re=s-1
syn region Question start='\c^To:' end='^[^ \t]'me=e-1,he=e-1,re=s-1
syn region PreProc start='\c^From:' end='^[^ \t]'me=e-1,he=e-1,re=s-1
syn region Special start='\c^Message-Id:' end='^[^ \t]'me=e-1,he=e-1,re=s-1
syn region Special start='\c^In-Reply-To:' end='^[^ \t]'me=e-1,he=e-1,re=s-1

syntax match Number '=== LAST REPLY ==='

syn match FmDiffDel  '^-.*$'
syn match FmDiffDel  '> -.*$'lc=2

syn match FmDiffADD  '^+.*$'
syn match FmDiffADD  '> +.*$'lc=2

syn match FmDiffLine  '^@@ .*$'
syn match FmDiffLine  '> @@ .*$'lc=2

syn match FmDiffHeader   '^diff.*$'
syn match FmDiffHeader   '> diff.*$'lc=2
syn match FmDiffHeader   '^index.*$'
syn match FmDiffHeader   '> index.*$'lc=2
syn match FmDiffHeader   '^--- .*$'
syn match FmDiffHeader   '> --- .*$'lc=2
syn match FmDiffHeader   '^+++ .*$'
syn match FmDiffHeader   '> +++ .*$'lc=2

hi def link  FmDiffHeader  TabLineSel
hi def link  FmDiffDel  Operator
hi def link  FmDiffAdd  Function
hi def link  FmDiffLine  Identifier

hi DiffHeader gui=bold term=bold
