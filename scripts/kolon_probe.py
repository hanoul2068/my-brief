"""임시 조사용: 아울렛 카테고리의 브랜드 필터 동작 확인"""
from playwright.sync_api import sync_playwright

BASE = "https://www.kolonmall.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CAT = f"{BASE}/Category/List/133010030000"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_context(user_agent=UA, locale="ko-KR", viewport={"width": 1400, "height": 1000}).new_page()
    gql = []
    page.on("response", lambda r: gql.append(r) if "getCategoryFilterBrand" in r.url else None)
    page.goto(CAT, wait_until="networkidle", timeout=60000)

    for r in gql:
        body = r.text()
        print("FILTER_BRAND len", len(body))
        for kw in ["247", "24/7", "CUSTOMELLOW", "커스텀멜로우"]:
            i = body.find(kw)
            print(f"  [{kw}]", body[max(0, i - 200):i + 200] if i >= 0 else "-")

    # 추천브랜드의 '커스텀멜로우' 클릭 → URL 변화
    try:
        page.get_by_text("커스텀멜로우", exact=True).first.click()
        page.wait_for_timeout(4000)
        print("CLICK 커스텀멜로우 →", page.url)
        print("  상품수", page.evaluate("document.querySelectorAll('a[href*=\"/Product/\"]').length"))
    except Exception as e:
        print("click fail", e)

    # '브랜드' 필터 열고 247 찾기
    page.goto(CAT, wait_until="networkidle")
    try:
        page.get_by_text("브랜드", exact=True).last.click()
        page.wait_for_timeout(2500)
        txt = page.evaluate("document.body.innerText")
        for kw in ["24/7", "247", "시리즈"]:
            import re
            for m in list(re.finditer(re.escape(kw), txt))[:5]:
                print(f"  BRANDLIST[{kw}]", txt[max(0, m.start() - 40):m.start() + 40].replace("\n", " / "))
        loc = page.get_by_text(re.compile(r"^24/7"), exact=False)
        print("  24/7 후보 수", loc.count())
        if loc.count():
            loc.first.click()
            page.wait_for_timeout(1500)
            for t in ["적용", "확인", "상품보기", "검색"]:
                btn = page.get_by_text(re.compile(t))
                if btn.count():
                    btn.last.click()
                    break
            page.wait_for_timeout(4000)
            print("CLICK 24/7 →", page.url)
            print("  상품수", page.evaluate("document.querySelectorAll('a[href*=\"/Product/\"]').length"))
            for l in page.evaluate("[...document.querySelectorAll('a[href*=\"/Product/\"]')].slice(0,5).map(a=>a.href+' | '+(a.closest('li')||a).innerText.replace(/\\s+/g,' ').slice(0,120))"):
                print("   ", l)
    except Exception as e:
        print("brand filter fail", e)
    b.close()
