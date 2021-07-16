
runtime syntax/frainuilist.vim

""syn keyword Type PATCH
""syn keyword Function Re
syn match Identifier '\] \w\+:'ms=s+1

syn match LineNr '|'
syn match LineNr '\\'
syn match LineNr '-->'
syn match LineNr '==>'
syn match LineNr '`'
syn match Label '*'
syn match String '#'
syn match String 'Reply-UNDONE'
syn match Type '⚑'
syn match Identifier '- .*$'
syn match Identifier '+ .*$'
syn match PmenuSel   '+ @.*$'
syn match PmenuSel   '- @.*$'
syn match CursorLineNr ' \.\.\.\.\.\.'

syntax match FrainUiSig "\\subject;"     conceal cchar=\ contained
syntax match FrainUiSig "\\name;"     conceal cchar=\ contained
syntax match FrainUiSig "\\Me;"       conceal cchar=\ contained
syntax match FrainUiSig "\\time;"     conceal cchar=\ contained
syntax match FrainUiSig "\\shortmsg;" conceal cchar=\ contained
syntax match FrainUiSig "\\unread;"   conceal cchar=\ contained
syntax match FrainUiSig "\\end;"      conceal cchar=\ contained

syntax match MailSubject   "\\subject;[^\\]*\\end;"   contains=FrainUiSig
syntax match MailName   "\\name;[^\\]*\\end;"   contains=FrainUiSig
syntax match MailMe   "\\Me;[^\\]*\\end;"   contains=FrainUiSig
syntax match MailShortMsg   "\\shortmsg;[^\\]*\\end;"   contains=FrainUiSig
syntax match MailTime   "\\time;[^\\]*\\end;"   contains=FrainUiSig
syntax match Label   "\\unread;[^\\]*\\end;"   contains=FrainUiSig

hi def link MailTime Type
hi def link MailName ModeMsg
hi def link MailMe Type
hi def link MailSubject MoreMsg
hi MailShortMsg guifg=#867979
hi clear  CursorLine
hi def CursorLine  cterm=underline
