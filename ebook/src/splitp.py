import re,sys
LIM=115
def split_p(m):
    attrs, inner = m.group(1), m.group(2)
    if '<br' in inner or 'class="note"' in attrs or 'class="teacher"' in attrs: return m.group(0)
    text=re.sub(r'<[^>]+>','',inner)
    if len(text)<=LIM: return m.group(0)
    # candidate sentence boundaries outside tags with balanced inline tags
    cuts=[]
    for mm in re.finditer(r'(?<=[다요죠까])[.?!]["”’]?\s+', inner):
        pre=inner[:mm.end()]
        opens=len(re.findall(r'<(b|span|strong|em)\b',pre)); closes=len(re.findall(r'</(b|span|strong|em)>',pre))
        if opens==closes and pre.count('<')==pre.count('>'): cuts.append(mm.end())
    if not cuts: return m.group(0)
    parts=[];start=0
    sents=[];prev=0
    for c in cuts+[len(inner)]:
        sents.append(inner[prev:c].strip()); prev=c
    sents=[s for s in sents if s]
    cur=''
    for s in sents:
        t=re.sub(r'<[^>]+>','',cur+s)
        if cur and len(t)>LIM: parts.append(cur.strip()); cur=s+' '
        else: cur+=s+' '
    if cur.strip(): parts.append(cur.strip())
    return ''.join(f'<p{attrs}>{p}</p>' for p in parts)
for f in sys.argv[1:]:
    s=open(f).read()
    s2=re.sub(r'<p((?:\s[^>]*)?)>(.*?)</p>',split_p,s,flags=re.S)
    open(f,'w').write(s2)
    print(f, s.count('<p'), '->', s2.count('<p'))
