import glob,re,sys
parts=sorted(glob.glob('v3/[0-9]*.html'))
s=''.join(open(p).read() for p in parts)
for m in set(re.findall(r'\{\{([A-Z_]+)\}\}',s)):
    s=s.replace('{{%s}}'%m, open('v3/'+m.lower().replace('chart_','chart_')+'.svg').read() if False else open(f'v3/{m.lower()}.svg').read())
if '</body>' not in s: s+='</body></html>'
open('html/v3.html','w').write(s)
print(len(parts),'parts')
