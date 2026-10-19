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

# 아울렛 전용 봇이 있으면 그 봇으로, 없으면 뉴스 브리핑 봇으로 보낸다
TELEGRAM_TOKEN = os.getenv("KOLON_TELEGRAM_TOKEN") or os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("KOLON_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
DRY_RUN = os.getenv("DRY_RUN") == "1"  # 1이면 텔레그램 전송/상태 저장 안 함 (테스트용)
DEBUG = os.getenv("DEBUG_SHOTS") == "1"
MANUAL = os.getenv("MANUAL_RUN") == "1"  # 직접 실행(Run workflow)이면 새 상품이 없어도 결과를 알려준다

BASE = "https://www.kolonmall.com"
# 코오롱몰 '아울렛' 카테고리. supplierBrands 로 브랜드를 걸러 볼 수 있다.
OUTLET_CATEGORY = f"{BASE}/Category/List/133010030000"
MAX_PAGES = 30  # 지난 시즌 상품이 아울렛으로 넘어오면 뒤쪽 페이지에 섞이므로 전체를 훑는다

BRANDS = [
    {
        "id": "247",
        "name": "247",
        "supplier_codes": ["TS_B191212171713"],
        "extra_lists": [],
        # 목록이 정말 이 브랜드 상품인지 확인할 때 쓰는 단서
        "keywords": ["247", "24/7"],
        "url_hints": ["/Brands/247/"],
    },
    {
        "id": "CUSTOMELLOW",
        "name": "커스텀멜로우",
        "supplier_codes": ["CW_B1"],
        # 커스텀멜로우 브랜드관 안의 OUTLET 메뉴
        "extra_lists": [f"{BASE}/Brands/CUSTOMELLOW/List/133020164494"],
        "keywords": ["CUSTOMELLOW", "커스텀멜로우"],
        "url_hints": ["/Brands/CUSTOMELLOW/"],
    },
]

PRODUCT_RE = re.compile(r"/Product/([A-Z0-9]{8,24})", re.I)
BADGE_WORDS = {"타임딜", "신상품", "베스트", "단독", "품절임박", "무료배송", "쿠폰"}
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
      img: img ? (img.currentSrc || img.src || img.getAttribute('data-src') || '') : '',
    });
  }
  return out;
}
"""

FIRST_PRODUCT_JS = "(document.querySelector('a[href*=\"/Product/\"]') || {}).href || ''"


# =========================
# 2. 크롤링
# =========================
def parse_card(raw: dict, brand: dict) -> dict | None:
    m = PRODUCT_RE.search(raw.get("href", ""))
    if not m:
        return None
    code = m.group(1).upper()
    text = raw.get("text", "")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 이름: 배지·브랜드명·숫자가 아닌 줄 중 가장 긴 것
    skip = BADGE_WORDS | {k.lower() for k in brand["keywords"]} | {brand["name"].lower()}
    candidates = [l for l in lines
                  if l.lower() not in skip
                  and not re.fullmatch(r"[\d,.%원\s~()+]+", l)
                  and len(l) > 2]
    name = max(candidates, key=len) if candidates else code

    prices = [int(p.replace(",", "")) for p in re.findall(r"(\d{1,3}(?:,\d{3})+)\s*원", text)]
    discount = re.search(r"(\d{1,2})\s*%", text)
    return {
        "code": code,
        "name": name,
        "url": f"{BASE}/Product/{code}",
        "href": raw.get("href", ""),
        "price": min(prices) if prices else None,
        "orig_price": max(prices) if len(prices) > 1 else None,
        "discount": int(discount.group(1)) if discount else None,
        "img": raw.get("img", ""),
        "text": text,
    }


def matches_brand(item, brand) -> bool:
    if any(h.lower() in item["href"].lower() for h in brand["url_hints"]):
        return True
    for kw in brand["keywords"]:
        # "247"처럼 숫자 키워드는 가격(124,700원 등)에 섞이지 않도록 경계를 확인
        if re.search(rf"(?<![\d,]){re.escape(kw)}(?![\d,])", item["text"], re.I):
            return True
    return False


def wait_products(page):
    try:
        page.wait_for_selector('a[href*="/Product/"]', timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(1500)


def go_next_page(page, n) -> bool:
    """페이지 번호 버튼(n)을 눌러 다음 목록으로 이동. 없으면 False."""
    btn = page.locator("button, a").filter(has_text=re.compile(rf"^\s*{n}\s*$"))
    if btn.count() == 0:
        return False
    before = page.evaluate(FIRST_PRODUCT_JS)
    btn.last.scroll_into_view_if_needed()
    btn.last.click()
    for _ in range(20):
        page.wait_for_timeout(500)
        if page.evaluate(FIRST_PRODUCT_JS) != before:
            page.wait_for_timeout(800)
            return True
    return False


def collect_list(page, url, brand, verify, debug):
    """목록 페이지(최대 MAX_PAGES)를 돌며 상품을 모은다."""
    print(f"🔎 {url}")
    items = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        wait_products(page)
        for n in range(1, MAX_PAGES + 1):
            if n > 1 and not go_next_page(page, n):
                print(f"  ⚠️ {n}페이지 버튼을 찾지 못해 여기서 멈춤")
                break
            got = [p for p in (parse_card(r, brand) for r in page.evaluate(EXTRACT_JS)) if p]
            items.extend(got)
            print(f"  → {n}페이지 상품 {len(got)}개")
            if len(got) < 20:  # 마지막 페이지
                break
    except Exception as e:
        print(f"  ⚠️ 페이지 열기 실패: {e}")
        debug["pages"].append({"url": url, "error": str(e)})
        return []

    if verify and items:
        ok = [it for it in items if matches_brand(it, brand)]
        # 필터가 먹지 않아 다른 브랜드가 섞여 나오면 해당 목록은 버린다
        if len(ok) < len(items) * 0.5:
            print(f"  ⚠️ 브랜드 필터가 적용되지 않은 듯 ({len(ok)}/{len(items)}) → 이 목록은 건너뜀")
            items = []
        else:
            items = ok

    debug["pages"].append({"url": url, "final_url": page.url, "products": len(items)})
    if DEBUG:
        for it in items[:3]:
            print(f"  예시: {it['code']} | {it['name']} | {it['price']} / {it['orig_price']} ({it['discount']}%)")
    return items


def collect_outlet_products():
    found = {}  # code -> item
    debug = {"pages": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, locale="ko-KR", viewport={"width": 1400, "height": 1000})
        page = ctx.new_page()

        for b in BRANDS:
            lists = [(f"{OUTLET_CATEGORY}?supplierBrands={c}&sort=newProduct-desc", True)
                     for c in b["supplier_codes"]]
            lists += [(u + "?sort=newProduct-desc", False) for u in b["extra_lists"]]
            for url, verify in lists:
                for it in collect_list(page, url, b, verify, debug):
                    found.setdefault(it["code"], {**it, "brand": b["id"], "brand_name": b["name"]})

        browser.close()

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

    counts = {b["id"]: sum(1 for it in items if it["brand"] == b["id"]) for b in BRANDS}
    for b in BRANDS:
        print(f"📦 {b['name']}: 아울렛 상품 {counts[b['id']]}개")

    if not items:
        # 사이트 구조가 바뀌었거나 접속이 막힌 경우 → 기존 기록을 지키고 실패로 종료
        print("❌ 아울렛 상품을 하나도 찾지 못했습니다. 사이트 구조를 확인해야 합니다.")
        sys.exit(1)

    state = load_state()
    now = datetime.now(KST).isoformat(timespec="seconds")

    if state is None:
        # 첫 실행: 지금 있는 상품을 기준으로 삼고, 시작 알림만 보낸다
        state = {"seen": {}}
        summary = ", ".join(f"{b['name']} {counts[b['id']]}개" for b in BRANDS)
        send_to_telegram(f"✅ <b>코오롱몰 아울렛 알림봇 시작</b>\n현재 아울렛 상품: {summary}\n"
                         f"이제부터 새로 올라오는 상품만 알려드릴게요.")
    else:
        new_items = [it for it in items if it["code"] not in state["seen"]]
        print(f"🆕 새 상품 {len(new_items)}개")
        if new_items:
            notify_new(new_items)
        elif MANUAL:
            summary = ", ".join(f"{b['name']} {counts[b['id']]}개" for b in BRANDS)
            send_to_telegram(f"🔎 <b>코오롱몰 아울렛 확인 완료</b>\n새 상품은 없어요.\n현재 아울렛 상품: {summary}")

    # 기록은 새 상품이 있을 때만 바뀌므로, 아무 일 없는 시간에는 커밋도 생기지 않는다
    for it in items:
        state["seen"].setdefault(it["code"], {"name": it["name"], "brand": it["brand"], "first_seen": now})

    if DRY_RUN:
        print("(DRY_RUN) 상태 파일은 저장하지 않습니다.")
    else:
        save_state(state)


if __name__ == "__main__":
    main()
