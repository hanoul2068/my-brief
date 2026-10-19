"""임시 조사용: 코오롱몰 페이지 구조(메뉴, 필터, API)를 로그로 출력"""
import json
from playwright.sync_api import sync_playwright

BASE = "https://www.kolonmall.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

LINKS_JS = r"""
(pat) => [...document.querySelectorAll('a[href]')]
  .filter(a => new RegExp(pat, 'i').test(a.getAttribute('href')))
  .map(a => (a.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 40) + ' => ' + a.getAttribute('href'))
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_context(user_agent=UA, locale="ko-KR", viewport={"width": 1400, "height": 1000}).new_page()
    api = []
    page.on("request", lambda r: api.append(f"{r.method} {r.url} {r.post_data or ''}"[:400])
            if r.resource_type in ("xhr", "fetch") else None)

    for url, pat in [
        (f"{BASE}/Brands/247", r"/Brands/247/(List|Special|Outlet)|outlet|Sale"),
        (f"{BASE}/Category/List/133010030000", r"Category|brand|Brand|page="),
        (f"{BASE}/Brands/CUSTOMELLOW/List/133020164494", r"page=|List/1330201644"),
    ]:
        api.clear()
        print("\n========", url)
        page.goto(url, wait_until="networkidle", timeout=60000)
        print("최종:", page.url)
        for l in sorted(set(page.evaluate(LINKS_JS, pat)))[:80]:
            print("  L", l)
        # 브랜드 필터 버튼/체크박스 텍스트
        txt = page.evaluate("document.body.innerText")
        for kw in ["247", "커스텀멜로우", "브랜드", "전체", "개의 상품", "총"]:
            i = txt.find(kw)
            print(f"  T[{kw}]", txt[max(0, i - 60):i + 80].replace("\n", " / ") if i >= 0 else "-")
        for a in api:
            if "kolonmall" in a and not any(x in a for x in (".js", ".css", "log", "analytics")):
                print("  API", a)

    # 아울렛 카테고리에서 스크롤/더보기 시 주소·요청 변화 확인
    api.clear()
    page.goto(f"{BASE}/Category/List/133010030000", wait_until="networkidle")
    for _ in range(6):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(1500)
    print("\n스크롤 후 상품 링크 수:", page.evaluate("document.querySelectorAll('a[href*=\"/Product/\"]').length"), page.url)
    for a in api:
        if "kolonmall" in a:
            print("  API2", a)
    print("페이지네이션:", page.evaluate(r"""[...document.querySelectorAll('button,a')].filter(e=>/^(\d+|다음|더보기|next)$/i.test((e.innerText||'').trim())).map(e=>e.tagName+':'+e.innerText.trim()+':'+(e.getAttribute('href')||'')).slice(0,20)"""))
    b.close()
