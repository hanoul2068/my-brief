import re
def renum(s):
    c=[0]
    def a(m): c[0]+=1; return f'<span class="st">STEP {c[0]}</span>'
    s=re.sub(r'<span class="st">STEP \d+</span>',a,s); N=c[0]; d=[0]
    def b(m): d[0]+=1; return f'<span>STEP {d[0]} / {N}</span>'
    return re.sub(r'<span>STEP \d+ / \d+</span>',b,s)
def page(n,chap,tp,title,body):
    return f'\n<section class="pg"><div class="body">\n  <div class="ph"><span class="st">STEP {n}</span><span class="tp">{tp}</span></div>\n  <h2 class="q">{title}</h2>\n{body}\n</div><div class="foot"><span>{chap}</span><span>STEP 0 / 0</span></div></section>\n'
def before(s,marker,html):
    i=s.index(marker); i=s.rindex('<section class="pg">',0,i); return s[:i]+html+s[i:]
