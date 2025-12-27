import os
import re
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import tz

# =========================
# 기본 설정
# =========================
KST = tz.gettz("Asia/Seoul")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "posts")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"

# =========================
# 한국 소식 소스 (출처=카테고리)
# =========================
SOURCES = [
    # ---- 언론사 ----
    {
        "id": "sbs_headline",
        "name": "SBS (이 시각 이슈)",
        "kind": "rss",
        "url": "https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER",
        "limit": 8,
    },
    {
        "id": "sbs_politics",
        "name": "SBS (정치)",
        "kind": "rss",
        "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER",
        "limit": 8,
    },
    {
        "id": "sbs_economy",
        "name": "SBS (경제)",
        "kind": "rss",
        "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02&plink=RSSREADER",
        "limit": 8,
    },
    {
        "id": "yonhap_tv_latest",
        "name": "연합뉴스TV (최신)",
        "kind": "rss",
        "url": "http://www.yonhapnewstv.co.kr/browse/feed/",
        "limit": 8,
    },
    {
        "id": "yonhap_tv_economy",
        "name": "연합뉴스TV (경제)",
        "kind": "rss",
        "url": "http://www.yonhapnewstv.co.kr/category/news/economy/feed/",
        "limit": 8,
    },
    {
        "id": "mk_economy",
        "name": "매일경제 (경제)",
        "kind": "rss",
        "url": "https://www.mk.co.kr/rss/30100041/",
        "limit": 8,
    },
    {
        "id": "mk_politics",
        "name": "매일경제 (정치)",
        "kind": "rss",
        "url": "https://www.mk.co.kr/rss/30200030/",
        "limit": 8,
    },
    {
        "id": "hankyung_economy",
        "name": "한국경제 (경제)",
        "kind": "rss",
        "url": "https://www.hankyung.com/feed/economy",
        "limit": 8,
    },
    {
        "id": "hankyung_politics",
        "name": "한국경제 (정치)",
        "kind": "rss",
        "url": "https://www.hankyung.com/feed/politics",
        "limit": 8,
    },

    # ---- 정부/정책 (정책브리핑) ----
    {
        "id": "koreakr_policy",
        "name": "정책브리핑 (정책뉴스)",
        "kind": "rss",
        "url": "https://www.korea.kr/rss/policy.xml",
        "limit": 10,
    },
    {
        "id": "koreakr_pressrelease",
        "name": "정책브리핑 (보도자료)",
        "kind": "rss",
        "url": "https://www.korea.kr/rss/pressrelease.xml",
        "limit": 10,
    },
    {
        "id": "koreakr_ebriefing",
        "name": "정책브리핑 (부처 브리핑)",
        "kind": "rss",
        "url": "https://www.korea.kr/rss/ebriefing.xml",
        "limit": 10,
    },
    {
        "id": "koreakr_fact",
        "name": "정책브리핑 (사실은 이렇습니다)",
        "kind": "rss",
        "url": "https://www.korea.kr/rss/fact.xml",
        "limit": 10,
    },
    # 주요 부처(원하면 더 늘릴 수 있음)
    {
        "id": "koreakr_moef",
        "name": "기획재정부 (정책브리핑)",
        "kind": "rss",
        "url": "https://www.korea.kr/rss/dept_moef.xml",
        "limit": 8,
    },
    {
        "id": "koreakr_molit",
        "name": "국토교통부 (정책브리핑)",
        "kind": "rss",
        "url": "https://www.korea.kr/rss/dept_molit.xml",
        "limit": 8,
    },
    {
        "id": "koreakr_msit",
        "name": "과기정통부 (정책브리핑)",
        "kind": "rss",
        "url": "https://www.korea.kr/rss/dept_msit.xml",
        "limit": 8,
    },
]

# =========================
# 유틸
# =========================
def ensure_dir():
    os.makedirs(POSTS_DIR, exist_ok=True)

def now_kst_iso():
    return datetime.now(tz=KST).isoformat()

def clean_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()

def as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, dict):
        for k in ("#text", "text", "value", "name", "title"):
            if k in v:
                return as_text(v[k])
        return " ".join(as_text(x) for x in v.values()).strip()
    if isinstance(v, list):
        return " ".join(as_text(x) for x in v).strip()
    return str(v)

def fallback_summary(text: str, max_len=450) -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if len(t) <= max_len:
        return t
    cut = t[:max_len]
    last = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return (cut[: last + 1] if last > 140 else cut + "…").strip()

# =========================
# OpenAI 한국어 요약
# =========================
def openai_summary(title: str, content: str) -> str | None:
    if not OPENAI_API_KEY:
        return None

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "너는 한국 뉴스를 매일 읽기 좋게 정리하는 한국어 에디터다. "
                    "반드시 한국어로 자연스럽게 5문장으로 요약한다. "
                    "원문을 길게 복사하지 말고 의미를 재구성한다. "
                    "추측/과장 금지, 불확실하면 그렇게 명시한다."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"[제목]\n{title}\n\n"
                    f"[본문]\n{content}\n\n"
                    "위 글을 한국어로 5문장으로 요약해줘. "
                    "핵심 사실 → 맥락/배경 → 영향/시사점 순으로."
                ),
            },
        ],
        "temperature": 0.3,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=45)
    if r.status_code != 200:
        print("OpenAI call failed:", r.status_code)
        print("OpenAI error(head):", r.text[:300])
        return None

    data = r.json()

    out = as_text(data.get("output_text")).strip()
    if out:
        return out

    texts = []
    for block in data.get("output", []):
        for c in block.get("content", []):
            if isinstance(c, dict):
                if c.get("type") == "output_text" and c.get("text"):
                    texts.append(c["text"])
                elif c.get("text"):
                    texts.append(c["text"])

    out2 = "\n".join(t.strip() for t in texts if t and t.strip()).strip()
    return out2 or None

def summarize(title: str, raw: str) -> str:
    s = openai_summary(title, raw[:6000])
    return s if s else fallback_summary(raw)

# =========================
# RSS 수집
# =========================
def fetch_rss(source_id: str, source_name: str, url: str, limit: int):
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:limit]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()

        html = e.get("summary", "")
        if not html and e.get("content"):
            html = (e.get("content")[0].get("value") or "")

        raw = clean_text(html) or title
        published = e.get("published", "") or e.get("updated", "")

        items.append({
            "category": source_id,      # 출처=카테고리
            "source_id": source_id,
            "source": source_name,
            "title": title,
            "url": link,
            "published_at": published,
            "raw_text": raw,
        })
    return items

# =========================
# 메인
# =========================
def main():
    ensure_dir()
    print("DEBUG OPENAI_API_KEY set?:", bool(OPENAI_API_KEY))
    print("DEBUG OPENAI_MODEL:", repr(OPENAI_MODEL))

    collected = []
    for s in SOURCES:
        try:
            collected += fetch_rss(s["id"], s["name"], s["url"], s["limit"])
        except Exception as e:
            print("Fetch failed:", s["id"], e)

    # 중복 제거
    seen = set()
    items = []
    for it in collected:
        key = (it["title"], it["url"])
        if key in seen:
            continue
        seen.add(key)

        items.append({
            "category": it["category"],
            "source_id": it["source_id"],
            "source": it["source"],
            "title": it["title"],
            "url": it["url"],
            "published_at": it["published_at"],
            "summary": summarize(it["title"], it["raw_text"]),
        })

    data = {
        "generated_at": now_kst_iso(),
        "sources": [{"id": s["id"], "name": s["name"]} for s in SOURCES],
        "items": items[:60],
    }

    today = datetime.now(tz=KST).strftime("%Y-%m-%d")
    with open(os.path.join(POSTS_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(os.path.join(POSTS_DIR, f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(data['items'])} items")

if __name__ == "__main__":
    main()
