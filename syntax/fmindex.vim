
runtime syntax/frainuilist.vim

""syn keyword Type PATCH
""syn keyword Function Re
syn match Identifier '\] \w\+:'ms=s+1

syn match LineNr '|'
syn match LineNr '-->'
syn match LineNr '`'
syn match Label '*'
syn match String '#'
syn match Type '⚑'
syn match Identifier '- .*$'
syn match Identifier '+ .*$'
syn match PmenuSel   '+ @.*$'
syn match PmenuSel   '- @.*$'
syn match CursorLineNr ' \.\.\.\.\.\.'

syntax match FrainUiSig "\\name;" conceal cchar=\   contained
syntax match FrainUiSig "\\time;" conceal cchar=\   contained
syntax match FrainUiSig "\\end;"   conceal cchar=\   contained

syntax match MailName   "\\name;[^\\]*\\end;"   contains=FrainUiSig
syntax match MailTime   "\\time;[^\\]*\\end;"   contains=FrainUiSig

hi def link MailName MoreMsg
hi def link MailTime Type
