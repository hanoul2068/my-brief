const { chromium } = require('playwright-core');
(async () => {
  const [,, inp, out] = process.argv;
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const p = await b.newPage({ viewport: { width: 559, height: 1000 } });
  await p.goto('file://' + require('path').resolve(inp), { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.emulateMedia({ media: 'print' });
  const rep = await p.evaluate(() => [...document.querySelectorAll('.pg')].map((pg, i) => {
    const body = pg.querySelector('.body'); const foot = pg.querySelector('.foot');
    const avail = pg.clientHeight - (foot ? foot.offsetHeight + 8 : 0);
    const st = (pg.querySelector('.ph .st')||{}).textContent || '';
    const tp = (pg.querySelector('.foot span')||{}).textContent || '';
    return { i, label: tp.slice(0,6) + ' ' + st, used: body.scrollHeight, avail, pct: Math.round(100*body.scrollHeight/avail) };
  }));
  for (const r of rep) console.log((r.pct > 100 ? 'OVER ' : r.pct < 70 ? 'LOW  ' : 'ok   ') + r.label + ' ' + r.pct + '%');
  await p.pdf({ path: out, preferCSSPageSize: true, printBackground: true, displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="width:100%;font-size:7.5pt;color:#8a96a3;text-align:center;font-family:sans-serif"><span class="pageNumber"></span></div>' });
  await b.close();
})();
