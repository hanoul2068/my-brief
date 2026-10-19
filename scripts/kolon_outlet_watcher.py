"""
코오롱몰 아울렛 신상품 알림봇
- 247, 커스텀멜로우(CUSTOMELLOW) 두 브랜드의 아울렛 상품만 감시
- 새로 올라온 상품이 있을 때만 텔레그램으로 알림
- 이미 본 상품은 data/kolon_outlet_seen.json 에 저장

코오롱몰은 자바스크립트로 상품 목록을 그리기 때문에 Playwright(헤드리스 크롬)로 페이지를 연다.
"""
import os
import re
import sys
import json
import time
import html
from datetime import datetime

import requests
from dateutil import tz
from playwright.sync_api import sync_playwright

# =========================
# 1. 설정
# =========================
KST = tz.gettz("Asia/Seoul")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(ROOT, "data", "kolon_outlet_seen.json")
DEBUG_DIR = os.path.join(ROOT, "debug")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DRY_RUN = os.getenv("DRY_RUN") == "1"  # 1이면 텔레그램 전송/상태 저장 안 함 (테스트용)

BASE = "https://www.kolonmall.com"
OUTLET_PAGE = f"{BASE}/View/Single/Outlet"

BRANDS = [
    {
        "id": "247",
        "name": "247",
        "pages": [f"{BASE}/Brands/247", f"{BASE}/247"],
        # 아울렛 전체 페이지에서 이 브랜드 상품을 골라낼 때 쓰는 단서
        "keywords": ["247", "24/7"],
        "url_hints": ["/Brands/247/", "/247/"],
    },
    {
        "id": "CUSTOMELLOW",
        "name": "커스텀멜로우",
        "pages": [f"{BASE}/Brands/CUSTOMELLOW", f"{BASE}/CUSTOMELLOW"],
        "keywords": ["CUSTOMELLOW", "커스텀멜로우"],
        "url_hints": ["/Brands/CUSTOMELLOW/", "/CUSTOMELLOW/"],
    },
]

OUTLET_WORDS = ["outlet", "아울렛"]
PRODUCT_RE = re.compile(r"/Product/([A-Z0-9]{8,20})", re.I)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# 페이지 안의 상품 카드 정보를 뽑는 JS
EXTRACT_JS = r"""
() => {
  const out = [];
  for (const a of document.querySelectorAll('a[href*="/Product/"]')) {
    // 이미지와 글자를 함께 가진 가장 가까운 상위 요소를 상품 카드로 본다
    let card = a;
    for (let i = 0; i < 6 && card.parentElement; i++) {
      const t = (card.innerText || '').trim();
      if (card.querySelector('img') && t.length > 5) break;
      card = card.parentElement;
    }
    const img = card.querySelector('img') || a.querySelector('img');
    out.push({
      href: a.href,
      text: (card.innerText || a.innerText || '').trim().slice(0, 400),
      title: a.getAttribute('title') || '',
      alt: img ? (img.getAttribute('alt') || '') : '',
      img: img ? (img.currentSrc || img.src || img.getAttribute('data-src') || '') : '',
    });
  }
  return out;
}
"""

# 브랜드 페이지 안의 'OUTLET/아울렛' 메뉴 링크를 찾는 JS
OUTLET_LINKS_JS = r"""
() => [...document.querySelectorAll('a[href]')]
  .filter(a => /outlet|아울렛/i.test((a.innerText || '') + ' ' + a.getAttribute('href')))
  .map(a => a.href)
"""


# =========================
# 2. 크롤링
# =========================
def is_outlet_text(text: str) -> bool:
    low = (text or "").lower()
    return any(w in low for w in OUTLET_WORDS)


def parse_card(raw: dict) -> dict | None:
    m = PRODUCT_RE.search(raw.get("href", ""))
    if not m:
        return None
    code = m.group(1).upper()
    lines = [l.strip() for l in raw.get("text", "").split("\n") if l.strip()]

    # 이름: title/alt 우선, 없으면 숫자·할인율·브랜드명이 아닌 가장 긴 줄
    name = raw.get("title") or raw.get("alt") or ""
    if not name:
        candidates = [l for l in lines if not re.fullmatch(r"[\d,.%원\s~]+", l) and len(l) > 3]
        name = max(candidates, key=len) if candidates else code

    prices = [int(p.replace(",", "")) for p in re.findall(r"(\d{1,3}(?:,\d{3})+)\s*원?", raw.get("text", ""))]
    discount = re.search(r"(\d{1,2})\s*%", raw.get("text", ""))
    return {
        "code": code,
        "name": name.strip(),
        "url": f"{BASE}/Product/{code}",
        "href": raw.get("href", ""),
        "price": min(prices) if prices else None,
        "orig_price": max(prices) if len(prices) > 1 else None,
        "discount": int(discount.group(1)) if discount else None,
        "img": raw.get("img", ""),
        "text": raw.get("text", ""),
    }


def scroll_to_bottom(page, max_rounds=25):
    """무한 스크롤 목록을 끝까지 내린다."""
    last = 0
    for _ in range(max_rounds):
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(1200)
        count = page.evaluate("document.querySelectorAll('a[href*=\"/Product/\"]').length")
        if count == last:
            break
        last = count


def open_and_collect(page, url, debug, tag):
    print(f"🔎 {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            page.wait_for_selector('a[href*="/Product/"]', timeout=20000)
        except Exception:
            pass
        scroll_to_bottom(page)
    except Exception as e:
        print(f"  ⚠️ 페이지 열기 실패: {e}")
        debug["pages"].append({"url": url, "error": str(e)})
        return [], []

    raws = page.evaluate(EXTRACT_JS)
    outlet_links = page.evaluate(OUTLET_LINKS_JS)
    items = [p for p in (parse_card(r) for r in raws) if p]
    print(f"  → 상품 {len(items)}개, 아울렛 링크 {len(set(outlet_links))}개 (최종 주소: {page.url})")
    debug["pages"].append({"url": url, "final_url": page.url, "products": len(items),
                           "outlet_links": sorted(set(outlet_links))[:30]})
    if os.getenv("DEBUG_SHOTS") == "1":
        print("  링크:", sorted(set(outlet_links))[:15])
        for it in items[:4]:
            print("  예시:", it["href"], "|", it["text"].replace("\n", " / ")[:150])
        os.makedirs(DEBUG_DIR, exist_ok=True)
        page.screenshot(path=os.path.join(DEBUG_DIR, f"{tag}.png"), full_page=False)
    return items, outlet_links


def is_brand_url(url, brand) -> bool:
    return any(h.lower() in url.lower() for h in brand["url_hints"])


def matches_brand(item, brand) -> bool:
    if is_brand_url(item["href"], brand):
        return True
    text = f'{item["name"]}\n{item["text"]}'
    for kw in brand["keywords"]:
        # "247"처럼 숫자 키워드는 가격(124,700원 등)에 섞이지 않도록 단어 경계로 확인
        if re.search(rf"(?<![\d,]){re.escape(kw)}(?![\d,])", text, re.I):
            return True
    return False


def collect_outlet_products():
    found = {}  # code -> item
    debug = {"pages": [], "json_urls": []}

    def add(item, brand, reason):
        if item["code"] not in found:
            found[item["code"]] = {**item, "brand": brand["id"], "brand_name": brand["name"], "reason": reason}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, locale="ko-KR", viewport={"width": 1400, "height": 1000})
        page = ctx.new_page()
        # 상품 목록 API 주소를 나중에 참고할 수 있도록 기록
        page.on("response", lambda r: debug["json_urls"].append(r.url)
                if "json" in (r.headers.get("content-type") or "") and len(debug["json_urls"]) < 200 else None)

        general_outlet_urls = set()
        visited = {OUTLET_PAGE, f"{BASE}/View/Outlet"}

        # (1) 코오롱몰 아울렛 전체 페이지 → 두 브랜드 상품만 골라내기
        items, _ = open_and_collect(page, OUTLET_PAGE, debug, "outlet")
        for it in items:
            for b in BRANDS:
                if matches_brand(it, b):
                    add(it, b, "outlet-page")

        # (2) 각 브랜드 페이지 → 'OUTLET' 메뉴를 찾아 들어가고, 상품명에 [Outlet]이 붙은 것도 수집
        for b in BRANDS:
            brand_outlet_urls = set()
            for url in b["pages"]:
                items, links = open_and_collect(page, url, debug, f"{b['id']}-main")
                for it in items:
                    if is_outlet_text(it["name"]):
                        add(it, b, "name-tag")
                for l in links:
                    if not l.startswith(BASE):
                        continue
                    # 브랜드 주소 안의 아울렛 메뉴만 그 브랜드 전용으로 본다.
                    # 그 밖의 링크(/View/Outlet 등 전체 아울렛)는 브랜드 판별을 거쳐야 한다.
                    if is_brand_url(l, b):
                        brand_outlet_urls.add(l)
                    else:
                        general_outlet_urls.add(l)
                if items:
                    break  # 첫 번째로 열린 브랜드 주소만 쓰면 충분
            for i, url in enumerate(sorted(brand_outlet_urls)[:5]):
                items, _ = open_and_collect(page, url, debug, f"{b['id']}-outlet{i}")
                for it in items:
                    add(it, b, "brand-outlet-menu")

        # (3) 전체 아울렛 성격의 다른 페이지들 → 브랜드 판별 후 수집
        for i, url in enumerate(sorted(general_outlet_urls - visited)[:5]):
            items, _ = open_and_collect(page, url, debug, f"general{i}")
            for it in items:
                for b in BRANDS:
                    if matches_brand(it, b):
                        add(it, b, "general-outlet")

        browser.close()

    debug["json_urls"] = sorted(set(debug["json_urls"]))
    return list(found.values()), debug


# =========================
# 3. 상태 저장 & 알림
# =========================
def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_to_telegram(text):
    if DRY_RUN or not TELEGRAM_TOKEN:
        print("[텔레그램 미전송]\n" + text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML",
               "disable_web_page_preview": True}
    try:
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code != 200:
            print(f"❌ 전송 실패: {res.text}")
    except Exception as e:
        print(f"❌ 오류: {e}")


def format_item(it):
    price = ""
    if it.get("price"):
        price = f"{it['price']:,}원"
        if it.get("orig_price") and it["orig_price"] > it["price"]:
            price = f"<s>{it['orig_price']:,}원</s> → <b>{price}</b>"
        if it.get("discount"):
            price += f" ({it['discount']}%↓)"
    line = f"• <a href=\"{it['url']}\">{html.escape(it['name'])}</a>"
    return line + (f"\n   {price}" if price else "")


def notify_new(new_items):
    now = datetime.now(KST).strftime("%m/%d %H:%M")
    for b in BRANDS:
        items = [it for it in new_items if it["brand"] == b["id"]]
        if not items:
            continue
        message = f"🛍 <b>코오롱몰 아울렛 신상</b> | {b['name']} {len(items)}개 ({now})\n━━━━━━━━━━━━━━\n"
        for it in items:
            chunk = format_item(it) + "\n"
            if len(message + chunk) > 3800:
                send_to_telegram(message)
                message = f"🛍 <b>{b['name']} (계속)</b>\n"
            message += chunk
        send_to_telegram(message)
        time.sleep(1)


def main():
    items, debug = collect_outlet_products()
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, "kolon_debug.json"), "w", encoding="utf-8") as f:
        json.dump({"items": items, **debug}, f, ensure_ascii=False, indent=2)

    for b in BRANDS:
        print(f"📦 {b['name']}: 아울렛 상품 {sum(1 for it in items if it['brand'] == b['id'])}개")

    if not items:
        # 사이트 구조가 바뀌었거나 접속이 막힌 경우 → 기존 기록을 지키고 실패로 종료
        print("❌ 아울렛 상품을 하나도 찾지 못했습니다. 사이트 구조를 확인해야 합니다.")
        sys.exit(1)

    state = load_state()
    now = datetime.now(KST).isoformat(timespec="seconds")

    if state is None:
        # 첫 실행: 지금 있는 상품을 기준으로 삼고, 시작 알림만 보낸다
        state = {"seen": {}}
        new_items = []
        counts = ", ".join(f"{b['name']} {sum(1 for it in items if it['brand'] == b['id'])}개" for b in BRANDS)
        send_to_telegram(f"✅ <b>코오롱몰 아울렛 알림봇 시작</b>\n현재 아울렛 상품: {counts}\n"
                         f"이제부터 새로 올라오는 상품만 알려드릴게요.")
    else:
        new_items = [it for it in items if it["code"] not in state["seen"]]
        print(f"🆕 새 상품 {len(new_items)}개")
        if new_items:
            notify_new(new_items)

    for it in items:
        state["seen"].setdefault(it["code"], {"name": it["name"], "brand": it["brand"], "first_seen": now})
    state["last_run"] = now

    if DRY_RUN:
        print("(DRY_RUN) 상태 파일은 저장하지 않습니다.")
    else:
        save_state(state)


if __name__ == "__main__":
    main()
